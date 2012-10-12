function [ f ] = dLdM0( M0, u0, alpha, beta, gam1, gam2 )
%DLDM0 Derivative of the bound with respect to M0
%   Detailed explanation goes here
[K,J] = size(alpha);

if M0 <= 0 % if M0 is undefined, set it equal to the value of M0=0
    M0 = eps;
end

for j = 1:J
    Eq1(j) = integral(@(x)Eq1kernel(x, M0, gam1(j), gam2(j)), 0, 1);
end
Eq1 = sum(Eq1);

for j = 1:J
    Eq2(j) = integral(@(x)Eq2kernel(x, M0, gam1(j), gam2(j)), 0, 1);
end
Eq2 = sum(Eq2);

f = K*J*psi(M0) + sum(gam1.*sum(psi(alpha)-psi(beta),1)) ...
    +sum(sum(psi(beta)-psi(alpha+beta))) -K*Eq1 - K*Eq2;

    function [f] = Eq1kernel(x, M0, gam1, gam2)
        f = normpdf(gam1,sqrt(gam2)).*x.*psi(x.*M0);
    end
    function [f] = Eq2kernel(x, M0, gam1, gam2)
        f = normpdf(gam1,sqrt(gam2)).*(1-x).*psi((1-x).*M0);
    end
end

