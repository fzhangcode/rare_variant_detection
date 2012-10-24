function [ u0,sigma20,M0,alpha,beta,gam1,gam2 ] = rvd2_est( r, n, u0, sigma20, M0 )
%RVD2_EST Estimate parameters for rvd2 model
%   Detailed explanation goes here

[K,J] = size(r);
MAXITER = 50; LLTOL = 1e-3;

%% Initialize variational parameters
gam1 = mean(r./n,1); gam2 = 0.05^2;
alpha = M0.*(r./n); beta = M0.*(1-r./n);


[ llCurr ] = ll_bound( r, n, u0, sigma20, M0, gam1, gam2, alpha, beta );
llDelta = Inf; iterCount =0; llSave = NaN(1,MAXITER);

while iterCount < MAXITER & llDelta > LLTOL
    
%     [ll] = plot_profile(r, n, u0, sigma20, M0, alpha, beta, gam1, gam2)

    %% Solve for u0
    u0 = mean(gam1);
    
    %% Solve for sigma20
    sigma20 = gam2 + mean((gam1-u0).^2);
    
    %% Solve for M0
    options = optimset('Display','iter');
%     M0 = fminbnd(@(x)-ll_bound(r, n, u0, sigma20, x, gam1, gam2, alpha, beta),...
%         0,1e10,options);
%     M0 = fzero(@(x)dLdM0( x, u0, alpha, beta, gam1, gam2 ), M0, options);
    
    % TODO: Do we want to loop over the variational parameters inside?
    for i = 1:1
        %% Solve for alpha & beta
        options = optimset('Display','off', 'UseParallel','always');
        for j = 1:J
            for k = 1:K
                alpha(k,j) = fzero(@(x)dLdalpha(x, beta(k,j),M0,u0,r(k,j),n(k,j)), alpha(k,j), options);
            end
        end

        options = optimset('Display','off');
        for j = 1:J
            for k = 1:K
                beta(k,j) = fzero(@(x)dLdbeta(alpha(k,j), x, M0,u0,r(k,j),n(k,j)), beta(k,j), options);
            end
        end

        %% Solve for gamma1 & gamma2
        options = optimset('Display','off');
        for j = 1:J
            gam1(j)= fzero(@(x)dLdgam1( x, gam2, alpha(:,j), beta(:,j), M0, u0, sigma20), gam1(j),...
                options);
        end

%         options = optimset('Display','iter');
%         gam2 = fminunc(@(x)(-ll_bound(r, n, u0, sigma20, M0, gam1, x, alpha, beta)),...
%             gam2,options);
         gam2= fzero(@(x)dLdgam2( gam1, x, M0, sigma20 ), gam2, options);
        
%         llSub = ll_bound( r, n, u0, sigma20, M0, gam1, gam2, alpha, beta )
    end
    %% Update the ll bound
    iterCount = iterCount+1;
    llSave(iterCount) = llCurr;
    llCurr = ll_bound( r, n, u0, sigma20, M0, gam1, gam2, alpha, beta );
    llDelta = (llCurr - llSave(iterCount))./abs(llSave(iterCount))
    
    assert(llDelta > 0, 'Error: Log-likelihood bound decreased.');
    
    %% Plot the current estimates
    plot_estimate( r, n, alpha, beta, gam1, u0, sigma20 )
    pause(1)
end

