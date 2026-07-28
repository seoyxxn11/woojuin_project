package com.ssafy.woojuin.domain.auth.oauth;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.service.OAuthAccountService;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.stereotype.Service;

@Service
public class CustomOidcUserService extends OidcUserService {

    private final OAuthAccountService oAuthAccountService;

    public CustomOidcUserService(OAuthAccountService oAuthAccountService) {
        this.oAuthAccountService = oAuthAccountService;
    }

    @Override
    public OidcUser loadUser(OidcUserRequest userRequest) {
        OidcUser oidcUser = super.loadUser(userRequest);
        GoogleUserInfo userInfo = new GoogleUserInfo(oidcUser.getClaims());

        User user = oAuthAccountService.findOrCreateUser(
                AuthProvider.GOOGLE, userInfo.getProviderId(), userInfo.getEmail(), userInfo.getNickname());

        return new CustomOidcUser(user.getId(), oidcUser);
    }
}
