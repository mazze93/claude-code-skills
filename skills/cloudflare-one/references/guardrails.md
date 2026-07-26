# Guardrails

- Access controls application authorization; Gateway controls traffic inspection/filtering. Use both when the requirement spans identity-aware app access and network/web security.
- Public hostname Access apps can be clientless. Private destination apps require WARP/Device client or another network on-ramp plus routes and DNS resolution. Retrieve [self-hosted private app](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/non-http/self-hosted-private-app/) docs before configuring private destinations.
- Cloudflare Tunnel is an off-ramp from a private network to Cloudflare. Cloudflare WAN and Mesh are other off-ramps which can also be on-ramps.
- Group-based policies depend on IdP group claims or SCIM. If group sync is missing, do not invent group selectors.
- Private hostnames need explicit DNS routing/resolution; creating an Access app alone is not enough. Use [resolver policies](https://developers.cloudflare.com/cloudflare-one/traffic-policies/resolver-policies/) and review [Connect a private hostname](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/private-net/cloudflared/connect-private-hostname/)
- HTTP inspection and DLP for encrypted web traffic require TLS inspection and planned Do Not Inspect exceptions.
- Gateway DNS, Network, HTTP, and Egress policies have different evaluation semantics. Retrieve [order of enforcement](https://developers.cloudflare.com/cloudflare-one/traffic-policies/order-of-enforcement/) docs before explaining precedence.
- Start broad block/allow/DLP/TLS policies disabled limited to a pilot with specific target users or groups unless the user approves a wider rollout.

### Identity and Access

- Access Groups are Cloudflare objects; IdP/SCIM groups are identity claims. Gateway group selectors use synced IdP groups, not Access Groups.
- Group names and SAML/OIDC attributes are case-sensitive. Verify exact claim names and values before creating group-based rules.
- SCIM changes and group membership can be stale until sync and re-authentication complete. Troubleshoot with the user's last authenticated identity, not just the IdP state.
- Access policies are default-deny. A private app with routes but no Allow policy still blocks access.
- Access policy selectors can use IP lists, not Gateway domain or URL lists.
- SaaS federation handles authentication into the SaaS app. SaaS authorization and tenant restrictions usually require SaaS-side roles and/or Gateway tenant controls.
- Browser Rendering for SSH/VNC/RDP is an Access capability. Browser Isolation renders general web content remotely. Do not conflate them.

### Device Client Deployment

- The [Cloudflare One device client](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/) is the on-ramp for user devices. Two components control it: **enrollment rules** (who can connect) and **device profiles** (how the client behaves after enrollment).
- The enrollment rule is an Access application of type `warp`, not a device setting. It accepts reusable Access policies. Look in Access for enrollment debugging, not Devices.
- For headless or autonomous devices (services, kiosks, Linux hosts), use service token enrollment. Non-human devices authenticate as `non_identity@[team-domain].cloudflareaccess.com` and have no group membership - device profiles targeting IdP groups will not match them. Target headless devices explicitly with the non-identity email, specific conventions about the devices (OS information, etc.),or let them fall to the default profile.
- Device profiles control connection mode, [split tunnel](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/route-traffic/split-tunnels/) configuration, user permissions (disable, switch lock), auto-reconnect, and captive portal behavior. Profiles are matched by user group or device attributes in precedence order - first match wins, default profile catches the rest.
- Split tunnel mode is the single most impactful client setting. Choose the mode based on the deployment goal:

  | Goal | Mode | Rationale |
  |---|---|---|
  | VPN replacement only (private apps) | **Include** | Route only specified private CIDRs and hostnames through the client. Everything else goes direct. Minimal blast radius. |
  | SWG only (internet security) | **Exclude** | All traffic through the client. Exclude only what breaks (local printers, certificate-pinned apps). |
  | VPN replacement + SWG | **Exclude** | All traffic through the client. Most common enterprise configuration. |
  | Coexistence with another VPN | **Include** | Avoids conflict with the other VPN's tunnel interface and DNS control. |
  | DNS filtering only | DNS-only mode | Only DNS queries go to Gateway. No traffic proxying. |

- Include vs exclude is per-profile, not per-entry. You cannot mix modes in the same profile. Switching modes mid-deployment requires re-evaluating every entry.
- Split tunnel entries must align with tunnel routes bidirectionally. A CIDR in the include list without a matching tunnel route causes a black hole. A tunnel route without a matching device profile entry means traffic never enters the tunnel.
- MDM parameters (`mdm.xml` / managed preferences) override dashboard-configured profile settings for any setting specified in the file. If dashboard changes appear to have no effect on managed devices, check MDM config. Retrieve [MDM deployment](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/deployment/mdm-deployment/) docs for platform-specific file locations and parameters.
- If another VPN client or agent controls DNS on the device, the device client's DNS interception will conflict. In coexistence scenarios, use "traffic only" mode to avoid routing table and DNS conflicts.
- Captive portal detection temporarily disconnects the client when it detects a portal (hotel WiFi, airport).  This is a common source of end-user friction and should be managed carefully.

### Private Networking

- Split tunnel mode changes the meaning of every route decision: Exclude mode sends traffic to Cloudflare when removed from excludes; Include mode sends traffic only when added to includes.
- Virtual networks should be used primarily when IP subnets overlap and hostname-based routing is not used. It can be used to control other user connectivity behavior, but it is recommended to manage through security policies.
- A healthy tunnel only proves cloudflared can reach Cloudflare. The tunnel must have appropriate published application routes, network routes, or hostname routes for connectivity to function.
- Cloudflare Tunnel and Cloudflare Mesh can both be used to facilitate connectivity to internal networks. Cloudflare WAN can as well, but it is gated behind Enterprise subscriptions. Retrieve [choose an on-ramp](https://developers.cloudflare.com/learning-paths/secure-internet-traffic/connect-devices-networks/choose-on-ramp/) when deliberating between Tunnel types.
- Run multiple cloudflared connectors for production HA, preferably on separate hosts. Token-based, remotely managed tunnels are the default for new deployments.

### Gateway, TLS, and DLP

- `dns.domains` matches a domain and subdomains; `dns.fqdn` is exact-match only.
- DNS pre-resolution selectors and post-resolution selectors do not behave like a single strict precedence list. Retrieve current evaluation docs before changing rule order.
- HTTP Do Not Inspect rules run before HTTP Allow/Block/Isolate behavior. A later block rule will not override an earlier inspection bypass.
- Certificate-pinned apps need Do Not Inspect exceptions before broad TLS inspection. Deploy the Cloudflare root CA to managed devices before enabling inspection.
- DLP profiles are detection definitions only. They do nothing until referenced by Gateway HTTP policies or CASB scan settings. Rules with body inspection may be evaluated multiple times in a single pass.
- Start DLP with payload logging where appropriate, tune false positives, then block.
- Gateway Network policies are strict L4 controls. Identity-aware L4 matching requires authenticated device context.

### CASB, Risk, and Operations

- API CASB is out-of-band and periodic. It does not provide real-time inline enforcement although some integrations support "remediation"; use Gateway granular application controls for inline CASB capability for supported applications. Retrieve [Granular application controls](https://developers.cloudflare.com/cloudflare-one/traffic-policies/http-policies/granular-controls/) when creating security policies for specific actions in specific SaaS applications.
- CASB findings are tied to specific assets and instances. Drill into affected assets before recommending remediation.
- Use current Dashboard remediation guidance for CASB fixes. Most remediations happen in the SaaS admin console, not Cloudflare.
- Large SaaS integrations can take 24-48 hours for initial scans. Reauthorizing can restart scan state; check credential health before reconnecting.
- User risk scores are behavior-based and asynchronous. CASB findings do not automatically imply high user risk.

### Infrastructure Access

- [Zero Trust Infrastructure Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/non-http/infrastructure-apps/) (ZTIA) is the purpose-built offering for SSH access through the device client. It provides capabilities not available through self-hosted apps: keystroke logging, control over how users authenticate to the target machine, [short-lived certificates](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/ssh-infrastructure-access/#generate-a-cloudflare-ssh-ca) that replace static SSH keys with ephemeral certs tied to Access identity, and lightweight privileged access management. Use Infrastructure Access apps for SSH when the device client is deployed.
- [Browser Rendering](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/non-http/browser-rendering/) provides clientless SSH, RDP, and VNC through the browser without requiring the device client. Clientless RDP includes session recording and file transfer controls. Use clientless access when a device client cannot be installed (contractors, partner access, unmanaged devices) - typically not as the default for managed users with the client installed.
- [Audit SSH](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/ssh-infrastructure-access/#enable-ssh-command-logging) is a Gateway Network policy action that logs SSH commands without blocking. It requires the session to be proxied through Cloudflare.
- Short-lived certificates require CA configuration on the target host and `sshd` configured to trust the Cloudflare CA public key. Retrieve [short-lived certificate setup](https://developers.cloudflare.com/cloudflare-one/identity/users/short-lived-certificates/) docs before configuring.
- For kubectl and database access behind private networks, use the device client with private destination routing. There is no Infrastructure Access or browser-rendered equivalent for arbitrary TCP protocols today.

### Logs, Analytics, and DEX

- [Gateway activity logs](https://developers.cloudflare.com/cloudflare-one/analytics/logs/gateway-logs/) record DNS, HTTP, and Network policy decisions. Filter by rule name, user identity, destination, action, and time range. These are the primary troubleshooting tool for "why was this blocked/allowed."
- [Access audit logs](https://developers.cloudflare.com/cloudflare-one/insights/logs/dashboard-logs/access-authentication-logs/) record authentication decisions per app - who authenticated, which policy matched, and session details. Use for verifying policy behavior and investigating access failures.
- [Shadow IT discovery](https://developers.cloudflare.com/cloudflare-one/insights/analytics/shadow-it-discovery/) uses Gateway HTTP logs to surface unmanaged SaaS applications. Requires TLS inspection for HTTPS visibility.
- [DEX (Digital Experience Monitoring)](https://developers.cloudflare.com/cloudflare-one/insights/dex/) provides fleet-level and per-device connectivity diagnostics. Use [DEX tests](https://developers.cloudflare.com/cloudflare-one/insights/dex/tests/) (HTTP, traceroute) to proactively monitor reachability to critical origins and internal apps. Fleet status shows device client health, connection mode, and connectivity state across the enrolled population.
- [Logpush](https://developers.cloudflare.com/cloudflare-one/analytics/logs/logpush/) exports Gateway, Access, Network, and DEX logs to external SIEM or storage. Configure before go-live if the customer requires centralized log retention or compliance reporting.
- When troubleshooting, work from logs toward config: identify the log entry showing the failure (Gateway block, Access deny, tunnel error, DNS resolution miss), then trace back to the responsible rule, route, or policy.

### Cloudflare WAN / Site Connectivity

- Cloudflare WAN is connectivity, not a security service. Apply inspection and policy with Gateway and Network Firewall where required.
- WAN firewall expressions are not the same language as Gateway wirefilter expressions. Retrieve the current syntax before editing.
- Generated IPsec PSKs and some OAuth/client secrets are returned once. Store them immediately.

