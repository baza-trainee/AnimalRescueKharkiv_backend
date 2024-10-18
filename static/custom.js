// custom.js
(function () {
  function updateAuthForm() {
    const oauth2Form = document.querySelector(".auth-container div div div");
    if (oauth2Form) {
      const username = oauth2Form.querySelector("#oauth_username");
      let domain_wrapper = oauth2Form.querySelector("#domain_wrapper");
      if (username) {
        const username_wrapper =
          username.parentElement.parentElement.parentElement;
        if (username_wrapper) {
          if (domain_wrapper == null) {
            const domainField = document.createElement("div");
            domainField.id = "domain_wrapper";
            domainField.className = "wrapper";
            username_wrapper.insertBefore(
              domainField,
              username_wrapper.firstChild,
            );
            domain_wrapper = domainField;
          }
        }
      }
      if (domain_wrapper) {
        domain_wrapper.innerHTML = `
                        <label for="domain">domain:</label>
                        <section class="block-tablet col-10-tablet block-desktop col-10-desktop">
                            <input id="domain" type="text" data-name="domain">
                        </section>
                    `;
      }
    }
  }

  function addCustomElements() {
    getAuthToken = function () {
      let auth = window.ui.auth();
      var securityToken = "";
      if (auth && auth._root && auth._root["entries"]) {
        auth._root["entries"].forEach((ent) => {
          if (ent[0] == "authorized") {
            if (ent[1] && ent[1]._root && ent[1]._root["entries"]) {
              ent[1]._root["entries"].forEach((ent1) => {
                if (ent1[0] == "OAuth2PasswordBearer") {
                  if (ent1[1] && ent1[1]._root && ent1[1]._root.nodes) {
                    ent1[1]._root.nodes.forEach((node) => {
                      if (node.constructor.name == "ValueNode" && node.entry) {
                        if (node.entry[0] == "token") {
                          if (
                            node.entry[1] &&
                            node.entry[1]._root &&
                            node.entry[1]._root.entries
                          ) {
                            node.entry[1]._root.entries.forEach((token) => {
                              if (token[0] == "access_token") {
                                securityToken = token[1];
                              }
                            });
                          }
                        }
                      }
                    });
                  }
                }
              });
            }
          }
        });
      }
      return securityToken;
    };

    const originalLogout = window.ui.authActions.logout;
    window.ui.authActions.logout = function (security) {
      const securityToken = getAuthToken();
      const authHeader = { Authorization: "Bearer " + securityToken };
      fetch("/auth/logout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + securityToken,
        },
      }).then((response) => {
        if (response.ok) {
          // Clear the token from Swagger UI
          originalLogout(security);
          updateAuthForm();
        } else {
          console.log("Logout failed");
        }
      });
    };

    buildFormData = function (data) {
      let s = [];
      for (let i in data) {
        let u = data[i];
        void 0 !== u &&
          "" !== u &&
          s.push([i, "=", encodeURIComponent(u).replace(/%20/g, "+")].join(""));
      }
      return s.join("&");
    };

    // Override the authorize function to include the domain field
    const originalAuthorizePassword = window.ui.authActions.authorizePassword;
    window.ui.authActions.authorizePassword = function (security) {
      const domainInput = document.getElementById("domain");
      if (domainInput) {
        const domain = domainInput.value;
        if (domain) {
          //security.domain = domain;
          let {
              schema: i,
              name: u,
              username: _,
              password: w,
              passwordType: x,
              clientId: C,
              clientSecret: j,
            } = security,
            L = {
              grant_type: "password",
              scope: security.scopes.join(" "),
              username: _,
              password: w,
              domain: domain,
            };
          security.bodyWithDomain = buildFormData(L);
        }
      }
      originalAuthorizePassword(security);
      const oauth2Form = document.querySelector(".auth-container div div div");
      if (oauth2Form) {
        const domain_wrapper = oauth2Form.querySelector("#domain_wrapper");
        if (domain_wrapper) {
          const domain_field = domain_wrapper.querySelector("#domain");
          if (domain_field) {
            value = domain_field.value;
            domain_wrapper.innerHTML = `
                                <div class="wrapper">
                                    <label for="domain">domain:</label>
                                    <code> ${value} </code>
                                </div>
                            `;
          }
        }
      }
    };

    const originalAuthorizeRequest = window.ui.authActions.authorizeRequest;
    window.ui.authActions.authorizeRequest = function (security) {
      const bodyWithDomain = security.auth.bodyWithDomain;
      if (bodyWithDomain) {
        security.body = bodyWithDomain;
      }
      originalAuthorizeRequest(security);
    };
  }

  function deleteClientCredentialFields(warpper) {
    pwd_type =
      wrapper.querySelector("#password_type").parentElement.parentElement;
    client_id_password = wrapper.querySelector("#client_id_password")
      .parentElement.parentElement;
    client_secret_password = wrapper.querySelector("#client_secret_password")
      .parentElement.parentElement;
    pwd_type.hide();
    client_id_password.hide();
    client_secret_password.hide();
  }

  // Wait for the Swagger UI to be fully loaded
  function waitForSwaggerUI() {
    const targetNode = document.querySelector(".swagger-ui");
    if (targetNode) {
      const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
          if (mutation.type === "childList") {
            const oauth2Form = document.querySelector(
              ".auth-container div div div",
            );
            if (oauth2Form) {
              addCustomElements();
            }
            updateAuthForm();
            observer.disconnect();
          }
        });
      });

      const config = { childList: true, subtree: true };
      observer.observe(targetNode, config);
    } else {
      setTimeout(waitForSwaggerUI, 100);
    }
  }

  waitForSwaggerUI();
})();
