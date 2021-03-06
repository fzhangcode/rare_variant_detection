__author__ = 'pjflaherty'


import numpy as np

import scipy as sp
from scipy import integrate
from scipy import stats
from scipy import optimize

import csv


class RVD21:
    """ RVD2 model class
    """
    def __init__(self, u0=None, sigma20=None, M0=None):
        if(u0 is None): self.u0 = np.float(0.4)
        else: self.u0=np.float(u0)

        if(sigma20 is None): self.sigma20 = np.float(np.power(0.1, 2))
        else:self.sigma20=np.float(sigma20)

        if(M0 is None): self.M0 = np.float(50)
        else: self.M0=np.float(M0)

    def __str__(self):
        return "u0=%0.3f | sigma20=%.3f | M0=%.1f" % (self.u0,self.sigma20,self.M0)

    def varest(self,r,n):
        K, J = r.shape
        MAXITER = 5
        LLTOL=0.001
        FLOATMAX = np.finfo(np.float64).max
        FLOATEPS = np.finfo(np.float64).eps

        def dLdM0(M0, alpha, beta, gam1, gam2):
            K, J = alpha.shape

            print M0
            def Eq1kernel(mu, M0, gam1, gam2):
                return sp.stats.norm.pdf(mu, loc=gam1, scale=np.sqrt(gam2)) * mu * sp.special.psi(mu*M0)
            def Eq2kernel(mu, M0, gam1, gam2):
                return sp.stats.norm.pdf(mu, loc=gam1, scale=np.sqrt(gam2)) * (1-mu) * sp.special.psi((1-mu)*M0)

            Eq1 = [sp.integrate.quad( lambda mu: Eq1kernel(mu,M0,gam1[j],gam2[j] ), 0, 1)[0] for j in xrange(J)]
            Eq1 = np.sum(Eq1)
            Eq2 = [sp.integrate.quad( lambda mu: Eq2kernel(mu,M0,gam1[j],gam2[j] ), 0, 1)[0] for j in xrange(J)]
            Eq2 = np.sum(Eq2)

            gam1K = np.tile(gam1, (K, 1) )

            return K*J*sp.special.psi(M0) -K*Eq1 -K*Eq2 \
                +np.sum(gam1K*sp.special.psi(alpha) +(1-gam1K)*sp.special.psi(beta) - sp.special.psi(alpha+beta))

        def dLdalpha(alpha, beta, r, n):
            return sp.special.polygamma(1,alpha)*(self.u0*self.M0 +r -alpha) \
                    -sp.special.polygamma(1,alpha+beta)*(self.M0 +n -(alpha+beta))

        def dLdbeta(alpha, beta, r, n):
            return sp.special.polygamma(1,beta)*((1-self.u0)*self.M0-1 +(n-r) -beta) \
                    -sp.special.polygamma(1,alpha+beta)*(self.M0+n-(alpha+beta))
        gam1 = np.tile(self.u0, J)
        gam2 = np.tile(self.sigma20, J)
        alpha = np.random.rand(K,J)
        beta = np.random.rand(K,J)

        iter = 0
        while iter < MAXITER:
            iter +=1

            # Update u0
            self.u0 = np.mean(gam1)

            # Update sigma20
            self.sigma20 = np.mean( gam2 + pow(gam1-u0, 2) )

            # Update M0
            self.M0 = sp.optimize.newton(lambda x: dLdM0(x, alpha, beta, gam1, gam2), tol=1e-2, \
                x0= 0.1 )
#            self.M0 = sp.optimize.brentq(lambda x: dLdM0(x, alpha, beta, gam1, gam2), a=1e-2, b=1e3 )


            # Update alpha
            alpha = [[ sp.optimize.newton(lambda x: dLdalpha(x, beta[k][j], r[k][j], n[k][j]), alpha[k][j], maxiter = 1000) \
                      for j in xrange(J) ] for k in xrange(K) ]
#            alpha = [[ sp.optimize.brentq(lambda x: dLdalpha(x, beta[k][j], r[k][j], n[k][j]), a=1e-3, b=1e6) \
#                      for j in range(J) ] for k in range(K) ]
#            alpha = np.array(alpha)

            # Update beta
#            beta = [[ sp.optimize.brentq(lambda x: dLdbeta(x, beta[k][j], r[k][j], n[k][j]), a=1e-3, b=1e6) \
#                       for j in xrange(J) ] for k in xrange(K) ]
#            beta = np.array(beta)

            print('%0.3f' % self.ll_bound(r,n,gam1,gam2,alpha,beta))
            print(self)




    def ll_bound(self, r, n, gam1, gam2, alpha, beta):
        K, J = r.shape

        def logG1(x, gam1, gam2, M0):
            return sp.stats.norm.pdf(x, loc=gam1, scale=np.sqrt(gam2)) * sp.special.gammaln(x*M0)
        def logG2(x, gam1, gam2, M0):
            return sp.stats.norm.pdf(x, loc=gam1, scale=np.sqrt(gam2)) * sp.special.gammaln((1-x)*M0)

        EqlogPmu = -0.5*np.log(2*np.pi*self.sigma20) -(0.5/self.sigma20)*(gam2 + np.power(gam1-u0,2))
        EqlogPmu = np.tile(EqlogPmu, (K,1) )

        EqlogG1 = [sp.integrate.quad( lambda x: logG1(x,gam1[j],gam2[j],self.M0 ), 0, 1)[0] for j in xrange(J)]
        EqlogG1 = np.array(EqlogG1)

        EqlogG2 = [sp.integrate.quad( lambda x: logG2(x,gam1[j],gam2[j],self.M0), 0, 1)[0] for j in xrange(J)]
        EqlogG2 = np.array(EqlogG2)

        EqlogPtheta = sp.special.gammaln(M0) -np.tile(EqlogG1+EqlogG2, (K,1)) \
                        + (self.u0*self.M0-1)*(sp.special.psi(alpha) - sp.special.psi(alpha+beta)) \
                        + ((1-self.u0)*self.M0-1)*(sp.special.psi(beta) - sp.special.psi(alpha+beta))


        EqlogPr = sp.special.gammaln(n+1) -sp.special.gammaln(r+1) -sp.special.gammaln(n-r+1) \
                    + r*(sp.special.psi(alpha)-sp.special.psi(alpha+beta)) \
                    + (n-r)*(sp.special.psi(beta)-sp.special.psi(alpha+beta))

        EqlogQmu = np.tile( -0.5*np.log(2*np.pi*np.exp(1)*gam2), (K,1) )

        EqlogQtheta = sp.special.gammaln(alpha+beta) -sp.special.gammaln(alpha) -sp.special.gammaln(beta) \
                        + (alpha-1)*sp.special.psi(alpha) + (beta-1)*sp.special.psi(beta) \
                        - (alpha + beta - 2)*sp.special.psi(alpha+beta)

        ll = EqlogPmu + EqlogPtheta + EqlogPr - EqlogQmu - EqlogQtheta
        return np.sum(ll)


if __name__ == "__main__":
    np.random.seed(1000)

    K = 3
    J = 10

    mod1 = RVD21(u0=0.8, sigma20=np.power(0.1,2), M0=50)
    print(mod1)

    u0 = 0.5
    sigma20 = np.power(0.1,2)

    M0 = 50
    mu = [np.random.normal(loc=u0, scale=np.sqrt(sigma20)) for i in range(J)]
    theta = [[np.random.beta(m*M0, (1-m)*M0) for m in mu] for k in range(K)]

    nL = np.array( [[100 for j in range(J)] for k in range(K)] )
    rL = np.array( [[np.random.binomial(nL[k][j],theta[k][j]) for j in range(J)] for k in range(K)] )

    with open('test_prof1.csv', 'rb') as f:
        reader = csv.reader(f)
        row = reader.next()
        rL = np.array(row[0::2])
        nL = np.array(row[1::2])

        for row in reader:



#    mod1.varest(rL,nL)