#!/usr/bin/env python

"""rvd23.py: Compute MAP estimates for RVD2.3 model."""

import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
from scipy.stats import gamma
from scipy.special import gammaln

import logging

K = 4 # Number of nucleotides

def generate_sample(phi, n=1000, nrep=1, npos=1):
    """Return a sample from the model"""
    
    # Draw M Dirichlet parameters
    alpha = gamma.rvs(phi['a'], scale=phi['b'], size=K*npos)
    alpha = np.reshape(alpha, (npos, K))
    
    # Draw the sample/replicate probabilities
    theta = np.zeros((nrep, npos, K))
    r = np.zeros((nrep, npos, K), dtype=np.int64)
    for i in xrange(0, nrep):
        for j in xrange(0, npos):
            theta[i,j,:] = np.random.mtrand.dirichlet(alpha[i,:])
            r[i,j,:] = np.random.multinomial(n, theta[i,j,:])
    
    return (r, alpha, theta)

def log_cond_alpha(phi, alpha, theta):
    """Return the log conditional distribution of alpha given its 
    Markov blanket.
    alpha = K-dimensional vector
    theta = NxK matrix with N replicates and K categories
    """
    
    nrep, K =  np.shape(theta)
    logPtheta = 0;
    for i in xrange(0,nrep):
        logPtheta = logPtheta \
                    + gammaln(np.sum(alpha)) \
                    - np.sum(gammaln(alpha)) \
                    + np.sum( (alpha-1) * np.log(theta[i,:]) )

    logPalpha = - gammaln(phi['a']) \
                - phi['a']*np.log(phi['b']) \
                + (phi['a']-1) * np.log(alpha) \
                - alpha/phi['b']
    logPalpha = np.sum(logPalpha)
    
    return (logPtheta + logPalpha)

def log_cond_theta(phi, alpha, theta, r):
    """Return the log conditional distribution of theta given its 
    Markov blanket.
    alpha = K-dimensional vector
    theta = K-dimensional vector
    r = K-dimensional vector of multinomial counts
    """
    
    n = np.sum(r) # total counts for multinomial
    
    logPr = gammaln(n+1) - np.sum(gammaln(r+1)) + np.sum(r * np.log(theta))
    
    logPtheta = gammaln(np.sum(alpha)) \
                - np.sum(gammaln(alpha)) \
                + np.sum( (alpha-1) * np.log(theta) )
                
    return (logPr + logPtheta)


def sample_alpha(alpha, theta, phi, nsample=1):
    """Return a sample from the posterior marginal distribution for alpha"""
    
    K = np.shape(alpha)[0]
    
    for s in xrange(0, nsample):
        # Compute the posterior likelihood for the current alpha
        logPalpha = log_cond_alpha(phi, alpha, theta)

        # Sample a non-negative value for alpha_p
        alpha_p = np.copy(alpha)
        for k in xrange(0,K):
            while True: 
                alpha_p[k] = np.random.normal(loc=alpha[k], scale=0.05)
                if alpha_p[k] > 0: break
            
        # Compute the posterior likelihood for the proposal alpha        
        logPalpha_p = log_cond_alpha(phi, alpha_p, theta)
    
        # Compute the acceptance probability
        prA = np.exp(np.min([0.0, logPalpha_p - logPalpha]))
  
        # Return the new value of alpha
        if (np.random.rand(1) < prA): 
            alpha = np.copy(alpha_p)

    return alpha

def sample_theta(alpha, theta, r, phi, nsample=1):
    """Generate a Metropilis-Hastings sample from the 
    marginal posterior of theta
    """
    
    K = np.shape(alpha)[0]
    
    for s in xrange(0, nsample):
        # Compute the posterior likelihood for the current theta
        logPtheta = log_cond_theta(phi, alpha, theta, r)
            
        # Sample a non-negative value for theta_p
        theta_p = np.copy(theta)
        for k in xrange(0,K):
            while True: 
                theta_p[k] = np.random.normal(loc=theta[k], scale=0.05)
                if 0 <= theta_p[k] <= 1: break
        theta_p = theta_p/np.sum(theta_p)
                
        # Compute the posterior likelihood for the proposal theta        
        logPtheta_p = log_cond_theta(phi, alpha, theta_p, r)
        
        # Compute the acceptance probability
        prA = np.exp(np.amin([0.0, logPtheta_p - logPtheta]))
            
        # Write the new value of alpha
        if (np.random.rand(1) < prA): 
            theta = np.copy(theta_p)
        
    return theta
        
def metro_gibbs(r, phi, nsample=10000):
    """Return samples from the posterior p(theta,alpha) 
    using Metropolis-within-Gibbs sampling.
    """
    
    # Get the size of the data set from r
    nrep, npos, K = np.shape(r)
    
    # Initialize alpha and theta
    alpha = gamma.rvs(1, scale=1, size=K*npos)
    alpha = np.reshape(alpha, (npos, K))
    
    theta = np.zeros((nrep, npos, K))
    for i in xrange(0, nrep):
        for j in xrange(0, npos):
            theta[i,j,:] = np.random.mtrand.dirichlet(alpha[i,:])

    # Draw nsample samples from the posterior distribution using M-H
    theta_s = np.zeros((nrep, npos, K, nsample))
    alpha_s = np.zeros((npos, K, nsample))
    for s in xrange(0,nsample):
        for j in xrange(0,npos):
            alpha[j,:] = sample_alpha(alpha[j,:], 
                                      theta[:,j,:], 
                                      phi, 
                                      nsample=1)
            for i in xrange(0, nrep):
                theta[i,j,:] = sample_theta(alpha[j,:], 
                                            theta[i,j,:], 
                                            r[i,j,:], 
                                            phi,
                                            nsample=1)
        alpha_s[:,:,s] = np.copy(alpha)
        theta_s[:,:,:,s] = np.copy(theta)

    return (alpha_s, theta_s)

if __name__ == '__main__':
    phi = {'a':1, 'b':2}
    r, alpha, theta = generate_sample(phi, npos=10, nrep=3)
    alpha_s, theta_s = metro_gibbs(r, phi, nsample=500)
    
    theta_hat = theta_s.mean(3)
    alpha_hat = alpha_s.mean(2)
    
    print "Estimated Alpha"
    print alpha_hat

    col = ('b', 'g', 'r', 'c')
    for i in xrange(0,4):
        plt.plot(range(0,10), theta[0,:,i], marker='+', ls='', color=col[i])
        plt.plot(range(0,10), theta_hat[0,:,i], color=col[i])
    plt.show()
    