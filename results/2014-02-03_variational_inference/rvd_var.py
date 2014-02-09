# -*- coding: utf-8 -*-
import numpy as np

import scipy.stats as ss
import scipy.optimize as so
from scipy.special import gammaln, psi, betaln
from scipy import linalg, integrate

#import pandas as pd

import multiprocessing as mp
from itertools import repeat

import h5py as h5
import tempfile
import logging
import time



def main():
    log_level = logging.DEBUG # default logging level
    logging.basicConfig(level=log_level,
        format='%(levelname)s:%(module)s:%(message)s')
    
  ## load the data
    
    pool = None
    #pool = mp.Pool(processes=2)
  ## model optimization  
    (phi, q) = varlap_opt(y, K=2, seed=10241978, pool=pool)

  ## save the parameters.

    save_model('model.hdf5', y, phi, q)
    

    

## compute sufficient statistics
def EqlogTheta(delta):
	return psi(delta[0]) - psi(np.sum(delta))

def Eqlog1_Theta(delta):
	return psi(delta[1]) - psi(np.sum(delta))

def EqMu(gam):
	return gam[0] / (np.sum(gam)) # eps?

def EqlogMu(gam):
	return psi(gam[0]) - psi(np.sum(gam))

def Eqlog1_Mu(gam):
	return psi(gam[1]) - psi(np.sum(gam))

def EqlogGamma(gam, M):
	# Eqlog\gam(muM)
	N = 7
	mu = range(0, 1 , 2^N+1)
	y = [kernel(gam[0], gam[1], x, M) for x in mu]

	return integrate.romb(y, dx = 0.1/(2^N+1))
	

def kernel(gam, mu, M):
		return ss.beta.pdf(mu, gam[0], gam[1])*betaln(mu*M, (1-mu)*M)


## compute entropy
def BetaEntropy(x):
	# To compute EqlogQmu and EqlogQtheta
	#return betaln(delta,gam) - (delta-1)psi(delta) - (gam - 1) psi(gam) +(delta + gam -2) psi(delta + gam)
	return betaln(x[0],x[1]) - (x[0]-1)psi(x[0]) - (x[1] - 1) psi(x[1]) +(x[0] + x[1] -2) psi(x[0] + x[1])


## compute ELBO
def ELBO(r, n, M, mu0, M0, delta, gam):
	(J,N) = n.shape

	Mu = [EqMu(gam[j,:]) for j in xrange(J)]
	logMu = [EqlogMu(gam[j,:]) for j in xrange(J)]
	log1_Mu = [Eqlog1_Mu(gam[j,:]) for j in xrange(J)]
	logTheta = [EqlogTheta(delta[j,i,:]) for j in xrange(J) for i in xrange(N)]
	log1_Theta = [Eqlog1_Theta(delta[j,i,:]) for j in xrange(J) for i in xrange(N)]

	EqlogPr = 0.0
	for j in xrange(J):
		for i in xrange(N):
			EqlogPr += - betaln(r[j,i] + 1, n[j,i] - r[j,i] +1)
			EqlogPr += r[j,i]*logTheta[j,i] + (n[j,i] - r[j,i]) * logTheta[j,i]

	EqlogPtheta = 0.0
	for j in xrange(J):
		EqlogPtheta += EqlogGamma(gam[j,:], M[j])
		for i in xrange(N):
			EqlogPtheta += (M[j]* Mu[j]- 1)*logTheta[j,i] +\
			(M[j]*(1 - Mu[j]) - 1)*log1_Theta[j,i]

	EqlogPmu = -betaln(mu0*M0, (1-mu0)*M0)
	for j in xrange(J):
		EqlogPmu += (M0*mu0-1)*logMu[j] + (M0*(1-mu0)-1)*log1_Mu[j]

	EqlogQtheta = 0.0
	for j in xrange(J):
		for i in xrange(N):
			EqlogQtheta += BetaEntropy(delta[j,i,:])

	EqlogQmu = 0.0
	for j in xrange(J):
			EqlogQmu += BetaEntropy(gam[j,i,:])

    return EqlogPr + EqlogPtheta + EqlogPmu - EqlogQtheta - EqlogQmu

def neg_ELBO_delta(logdelta, gam, r, n, M, mu0, M0):
    return -ELBO(r, n, M, mu0, M0, np.exp(logdelta), gam)

def opt_delta(r, n, M, mu0, M0, delta, gam):

    (J, N, _) = delta.shape

    bnds = [[[-7, 7],]] # limit delta to [0.0001, 10000]
    bnds = np.repeat(bnds, N, axis = 1)
    bnds = np.repeat(bnds, J, axis = 0)
    args=(gam, r, n, M, mu0, M0)

    logdelta = opt_par(neg_ELBO_delta, np.log(delta), args, bnds, 'gamma')
    delta = np.exp(logdelta)
    return delta

def neg_ELBO_gam(loggam, delta, r, n, M, mu0, M0):
    return -ELBO(r, n, M, mu0, M0, delta, np.exp(loggam))

def opt_gam(r, n, M, mu0, M0, delta, gam):
    
    (J, _) = gam.shape

    bnds = [[-7, 7],] # limit delta to [0.0001, 10000]
    bnds = np.repeat(bnds, J, axis = 0)
    args=(delta, r, n, M, mu0, M0), 
    loggam = opt_par(neg_ELBO_gam, np.log(gam), args, bnds, 'gamma')
    gam = np.exp(loggam)

    return gam

def neg_ELBO_mu0(mu0, r, n, M, M0, delta, gam):
    return -ELBO(r, n, M, mu0, M0, delta, gam)

def opt_mu0(r, n, M, mu0, M0, delta, gam):

    bnds = [0,1]
    args=(r, n, M, M0, delta, gam)
    mu0 = opt_par(neg_ELBO_mu0, mu0, args, bnds, 'mu0' )

    return mu0

def neg_ELBO_M0(logM0, mu0, M, r, n, delta, gam):
    return -ELBO(r, n, M, mu0, np.exp(logM0), delta, gam)
    
def opt_M0(r, n, M, mu0, M0, delta, gam):

    bnds = [-7,10]
    args = (mu0, M, r, n, delta, gam)
    logM0 = opt_par(neg_ELBO_M0, np.log(M0), args, bnds, 'M0' )
    M0 = np.exp(logM0)
    return M0

def neg_ELBO_M(logM, r, n, mu0, M0, delta, gam):
    return -ELBO(r, n, np.exp(logM), mu0, M0, delta, gam)


def opt_M(r, n, M, mu0, M0, delta, gam):
    
    bnds = [[-7, 7],] # limit delta to [0.0001, 10000]
    bnds = np.repeat(bnds, J, axis = 0)
    args = (r, n, mu0, M0, delta, gam)

    logM = opt_par(neg_ELBO_M, np.log(M)k, args, bnds, 'M')
    M = np.exp(logM)
    return M


def opt_par(func, x, args, bnds, par):
      res = so.minimize(func, x, \
        args=args, bounds=bnds, \
        method='L-BFGS-B')
    
    if res.success == False:
        res = so.minimize(func, x, \
            args=args, bounds=bnds, \
            method='Nelder-Mead')

    if res.success == False:
        so.minimize(func, x, \
            args=args, bounds=bnds, \
            method='BFGS')
    
    if res.success == False or np.any ( np.isnan(res.x) ):
        logging.warning("Could not optimize %s or %s is NaN." %(par, par))
        if bnds.dim = 1:
            size = 1
        else:
            size = np.shape(bnds)  
        x = np.random.uniform(low=bnds.amin, high=bnds.amax, size = size)      
        return x

    x = res.x
    return x



def ELBO_opt(r, n, phi = None, q = None, seed = None, pool = None):
	if seed is not None: np.random.seed(seed = seed)

    h5file = tempfile.NamedTemporaryFile(suffix='.hdf5')
    logging.info('Storing model updates in %s' % h5file.name)	

    ## Define optimization stopping criterion
    MAXITER = 20
    ELBOTOLPCT = 0.1    
    MAXVARITER = 10
    NORMTOL = 0.1


    (J, N) = n.shape
    ## Initialize model parameters
	if phi is None:
		phi, mu, theta = estimate_mom(r, n)
	else:
		_, mu, theta = estimate_mom(r, n)
	mu0 = phi['mu0']
	M0 = phi['M0']
	M = phi['M']

	## Initialize the variational parameters
	if q is None:
        delta = [r + mu*M+ np.finfo(np.float).eps, (n - r) + (1-mu)*M+ np.finfo(np.float).eps]
        gam = np.random.uniform(low=0.1, high=100, size(J,2))
	else:
		delta = q['delta']
		gam = q['gam']

    phi = {'mu0':mu0, 'M0':lam, 's2':s2}
    q = {'delta':delta, 'gam':gam}
    #save_model('initial_value.hdf5', r, n, phi, q)  

    ## Initialize ELBO
    elbo = [ELBO(r, n, M, mu0, M0, delta, gam)]
    logging.info("Initial ELBO: %0.2f" % elbo[-1])


    ## Optimization
    moditer = 0
    delta_elbo_pct = np.inf

    while moditer < MAXITER and delta_elbo_pct > ELBOTOLPCT:
    # E-step: Update the variational distribution


    variter = 0
    var_elbo = [ elbo[-1] ]
    (norm_delta_delta, norm_delta_gam) = (np.inf, np.inf)

        while variter < MAXVARITER \
            and delta_elbo_pct > ELBOTOLPCT \
            and (norm_delta_delta > NORMTOL or norm_delta_gam > NORMTOL):

            #Store the previous parameter values
            (delta_prev, gam_prev) = (np.copy(delta), np.copy(gam))

            #Update the variational distribution
            delta = opt_delta()
            gam = opt_gam()

            #Test for convergence

        # M-step: Update model parameters
        mu0 = opt_mu0()
        M0 = opt_M0()
        M = opt_M()

        # ibic

        # Display results for debugging

        # Store the model for viewing

    phi = {}
    q = {}

    return(phi, q)



def estimate_mom(r, n):
    """ Return model parameter estimates using method-of-moments.
    """

    theta = r/(n + np.finfo(np.float).eps) # make sure this is non-truncating division
    if np.ndim(r) == 1: mu = theta
    elif np.ndim(r) > 1: mu = np.mean(theta, 0)
    
    mu0 = np.mean(mu)
    M0 = (mu0*(1-mu0))/(np.var(mu) + np.finfo(np.float).eps)

    # estimate M. If there is only one replicate, set M as 10 times of M0.
    # If there is multiple replicates, set M according to the moments of beta distribution
    if np.shape(theta)[0] is 1:
        M = 10*M0*np.ones_like(mu)
    else:
        M = (mu*(1-mu))/(np.var(theta, 0) + np.finfo(np.float).eps )    

    phi = {'mu0':mu0, 'M0':M0, 'M':M}
    return phi, mu, theta

def save_model(fname, r, n, phi, q):

    f = h5.File(fname, 'w')
    
    f.create_dataset('r', data=r)
    f.create_dataset('n', data=n)

    f.create_group('phi')
    f['phi'].create_dataset('mu0', data=phi['mu0'])
    f['phi'].create_dataset('M0', data=phi['M0'])
    f['phi'].create_dataset('M', data=phi['M'])
    
    f.create_group('q')
    f['q'].create_dataset('delta', data=q['delta'])
    f['q'].create_dataset('gam', data=q['gam'])

    f.close()



def load_model(fname):
    
    f = h5.File(fname, 'r')
    
    r = f['r'][...]
    n = f['n'][...]

    phi = {}    
    phi['mu0'] = f['phi/mu0'][...]
    phi['M0'] = f['phi/M0'][...]
    phi['M'] = f['phi/M'][...]

    q = {}
    q['delta'] = f['q/delta'][...]
    q['gam'] = f['q/gam'][...]
    
    f.close()

    return (r, n, phi, q)
if __name__ == "__main__":
    main()
