# -*- coding: utf-8 -*-
"""
Created on Mon May 07 14:20:11 2018

@author: m.meliani
"""

from __future__ import print_function, division
import matplotlib

matplotlib.use("Agg")

import unittest
import numpy as np
import unittest
import inspect

from six import iteritems
from collections import OrderedDict

from smt.problems import Sphere, TensorProduct
from smt.sampling_methods import LHS, FullFactorial

from smt.utils.sm_test_case import SMTestCase
from smt.utils.silence import Silence
from smt.utils import compute_rms_error
from smt.surrogate_models import LS, QP, KPLS, KRG, KPLSK, GEKPLS, GENN
from smt.applications import MFK
from copy import deepcopy

print_output = False


class TestMFK(SMTestCase):
    def setUp(self):
        self.nt = 100
        self.ne = 100
        self.ndim = 3

    def test_mfk(self):
        self.problems = ["exp", "tanh", "cos"]

        for fname in self.problems:
            prob = TensorProduct(ndim=self.ndim, func=fname)
            sampling = FullFactorial(xlimits=prob.xlimits, clip=True)

            np.random.seed(0)
            xt = sampling(self.nt)
            yt = prob(xt)
            for i in range(self.ndim):
                yt = np.concatenate((yt, prob(xt, kx=i)), axis=1)

            y_lf = 2 * prob(xt) + 2
            x_lf = deepcopy(xt)
            np.random.seed(1)
            xe = sampling(self.ne)
            ye = prob(xe)

            sm = MFK(theta0=[1e-2] * self.ndim)
            if sm.options.is_declared("xlimits"):
                sm.options["xlimits"] = prob.xlimits
            sm.options["print_global"] = False

            sm.set_training_values(xt, yt[:, 0])
            sm.set_training_values(x_lf, y_lf[:, 0], name=0)

            with Silence():
                sm.train()

            t_error = compute_rms_error(sm)
            e_error = compute_rms_error(sm, xe, ye)

            self.assert_error(t_error, 0.0, 1)
            self.assert_error(e_error, 0.0, 1)

    def test_mfk_derivs(self):

        prob = Sphere(ndim=self.ndim)
        sampling = LHS(xlimits=prob.xlimits)

        nt = 500
        np.random.seed(0)
        xt = sampling(nt)
        yt = prob(xt)
        dyt = {}
        for kx in range(prob.xlimits.shape[0]):
            dyt[kx] = prob(xt, kx=kx)

        y_lf = 2 * prob(xt) + 2
        x_lf = deepcopy(xt)

        np.random.seed(1)
        xe = sampling(self.ne)
        ye = prob(xe)
        dye = {}
        for kx in range(prob.xlimits.shape[0]):
            dye[kx] = prob(xe, kx=kx)

        sm = MFK(theta0=[1e-2] * self.ndim)
        if sm.options.is_declared("xlimits"):
            sm.options["xlimits"] = prob.xlimits
        sm.options["print_global"] = False

        sm.set_training_values(xt, yt)
        sm.set_training_values(x_lf, y_lf, name=0)

        with Silence():
            sm.train()

        t_error = compute_rms_error(sm)
        e_error = compute_rms_error(sm, xe, ye)
        e_error0 = compute_rms_error(sm, xe, dye[0], 0)
        e_error1 = compute_rms_error(sm, xe, dye[1], 1)

        if print_output:
            print(
                "%8s %6s %18.9e %18.9e %18.9e %18.9e"
                % (pname[:6], sname, t_error, e_error, e_error0, e_error1)
            )

        self.assert_error(e_error0, 0.0, 1e-1)
        self.assert_error(e_error1, 0.0, 1e-1)

    @staticmethod
    def run_mfk_example(self):
        import numpy as np
        import matplotlib.pyplot as plt
        from smt.applications import MFK

        # Define the
        def LF_function(x):
            import numpy as np

            return (
                0.5 * ((x * 6 - 2) ** 2) * np.sin((x * 6 - 2) * 2)
                + (x - 0.5) * 10.0
                - 5
            )

        def HF_function(x):
            import numpy as np

            return ((x * 6 - 2) ** 2) * np.sin((x * 6 - 2) * 2)

        # Problem set up
        ndim = 1
        Xt_e = np.linspace(0, 1, 4, endpoint=True).reshape(-1, ndim)
        Xt_c = np.linspace(0, 1, 11, endpoint=True).reshape(-1, ndim)

        nt_exp = Xt_e.shape[0]
        nt_cheap = Xt_c.shape[0]

        # Evaluate the HF and LF functions
        yt_e = HF_function(Xt_e)
        yt_c = LF_function(Xt_c)

        sm = MFK(theta0=np.array(Xt_e.shape[1] * [1.0]))

        # low-fidelity dataset names being integers from 0 to level-1
        sm.set_training_values(Xt_c, yt_c, name=0)
        # high-fidelity dataset without name
        sm.set_training_values(Xt_e, yt_e)

        # train the model
        sm.train()

        x = np.linspace(0, 1, 101, endpoint=True).reshape(-1, 1)

        # query the outputs
        y = sm.predict_values(x)
        MSE = sm.predict_variances(x)
        der = sm.predict_derivatives(x, kx=0)

        plt.figure()

        plt.plot(x, HF_function(x), label="reference")
        plt.plot(x, y, linestyle="-.", label="mean_gp")
        plt.scatter(Xt_e, yt_e, marker="o", color="k", label="HF doe")
        plt.scatter(Xt_c, yt_c, marker="*", color="g", label="LF doe")

        plt.legend(loc=0)
        plt.ylim(-10, 17)
        plt.xlim(-0.1, 1.1)
        plt.xlabel(r"$x$")
        plt.ylabel(r"$y$")

        plt.show()


if __name__ == "__main__":
    unittest.main()
