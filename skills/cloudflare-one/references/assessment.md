# Assessment Prompts

Use these to avoid jumping straight to configuration. Ask only the prompts relevant to the user's task.

### Architecture and Current State

- Sites and users: offices, branches, data centers, VPCs, remote users, contractors, user counts, and current connectivity model.
- Applications and destinations: SaaS, public apps, private apps, APIs, infrastructure targets, protocols, ports, hostnames, and IP ranges.
- Connectivity: VPN, MPLS, SD-WAN, direct Internet breakout, centralized backhaul, site-to-site needs, and private DNS architecture.
- Security stack: current SWG, NGFW, VPN/ZTNA, DLP, CASB, email security, logging, and compliance requirements.
- Identity: IdP, SCIM/group sync, group naming, multi-IdP needs, service accounts, and contractor/partner access.
- Rollout: pilot users/sites, blast radius, rollback path, support owners, and success criteria.

### Access and SaaS Federation

- App shape: web app, API, SSH/RDP/VNC, database, SaaS app, public hostname, private IP, or private hostname. Retrieve [Access application type](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/choose-application-type/) docs before choosing.
- Access model: clientless browser access, private networking with device client, peer to peer connectivity, service connections with service tokens or mutual TLS, or SaaS SSO federation.
- Policy needs: user groups, device posture, session duration, mTLS, service tokens, and app launcher visibility. Retrieve [Access policy](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/) docs before configuring selectors or evaluation order.
- SaaS details: SAML vs OIDC support, ACS/redirect URLs, Entity IDs/client IDs, required attributes, and tenant-control requirements.

### Tunnel and Private Networking

- Sites and segments: which data centers, VPCs, offices, or network segments need connectivity.
- HA: dev/test single connector, production multiple connectors, or advanced multi-tunnel/site redundancy.
- Runtime: where cloudflared or WARP Connector/Mesh will run: VM, container, Kubernetes, bare metal, or other target.
- Egress: whether connectors can reach Cloudflare over the required outbound ports/protocols. Retrieve [Tunnel connectivity prechecks](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/troubleshoot-tunnels/connectivity-prechecks/) before naming exact endpoints.
- Origin reachability: whether the connector can resolve and reach every private origin.
- Routing: required CIDRs/hostnames, overlapping IP spaces, [virtual networks](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/private-net/cloudflared/tunnel-virtual-networks/), [Split Tunnels](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/route-traffic/split-tunnels/), and private DNS/[resolver policy](https://developers.cloudflare.com/cloudflare-one/traffic-policies/resolver-policies/) needs.
- Management model: prefer remotely managed/token-based tunnels for new deployments unless there is a clear reason for local config.

### Gateway, TLS, and DLP

- Traffic controls: DNS categories, HTTP URL/path inspection, L4 ports/protocols, egress IP requirements, custom lists, and allow/block exceptions. Retrieve [Gateway traffic policy](https://developers.cloudflare.com/cloudflare-one/traffic-policies/) docs for current selectors and order of enforcement.
- Identity: whether Gateway policies need user or group selectors, and whether users will be authenticated through WARP/IdP context. Check [Gateway identity selectors](https://developers.cloudflare.com/cloudflare-one/traffic-policies/identity-selectors/) and [SCIM provisioning](https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/scim/) when groups are involved.
- TLS inspection: root CA deployment path, certificate-pinned applications, compliance exceptions, and FIPS requirements. Retrieve [TLS decryption](https://developers.cloudflare.com/cloudflare-one/traffic-policies/http-policies/tls-decryption/) docs before enabling.
- DLP: sensitive data types, channels to inspect, TLS inspection readiness, DLP profiles, payload logging requirements, and false-positive tolerance. Retrieve [DLP](https://developers.cloudflare.com/cloudflare-one/data-loss-prevention/) docs before creating enforcement.

### CASB, Device Posture, and Risk

- CASB: SaaS vendors, admin access level, scan policy, org size, remediation owner, and whether inline protection is also required. Retrieve [CASB findings](https://developers.cloudflare.com/cloudflare-one/cloud-and-saas-findings/manage-findings/) docs before recommending remediation.
- Device posture: required checks, third-party EDR/MDM integrations, enrollment rules, device profiles, and split tunnel alignment.
- Risk scoring: relevant behavior signals, false-positive sources such as VPNs or service accounts, and whether risk is for investigation or enforcement. Retrieve [user risk score](https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/risk-score/) docs before using risk in policies.

### Cloudflare WAN / Site Connectivity

- Site topology, on-ramp type, route ownership, tunnel redundancy, static vs BGP-managed routes, network firewall needs, and appliance/profile ownership. Retrieve [Cloudflare WAN](https://developers.cloudflare.com/cloudflare-wan/) and [Cloudflare Network Firewall](https://developers.cloudflare.com/cloudflare-network-firewall/) docs before proposing site connectivity changes.

