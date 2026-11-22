# Threat model outline

**Asset.** Availability of explicitly selected noncritical lab services should follow the operator's physical USB presence policy. The host must retain SSH, network connectivity and console recovery in every supported transition.

**Trust boundary.** Trust the administrator, system manager, kernel, unit definitions and root-owned configuration, applied state and installation paths. Treat USB fields as hostile. A remote non-root user and an administrator who forgets to stop a service are in scope. An enrollment is identifier-only. Descriptors are clonable. Weak identifiers are eligible for observation only.

**Limits.** Root compromise, physical boot access, stolen or emulated devices, BadUSB/HID and direct access outside the managed units exceed this mechanism. Revocation can remove a stolen device's eligibility. A process or connection surviving its unit stop is relevant when deciding whether that unit is eligible. SSH authentication and device authorization remain independent controls.

**Exposure.** From physical removal, account for event delivery or next successful scan, manager scheduling and lock delay, enumeration/settle, remaining grace, any delay to the expiry check, and actual stop completion. Some intervals can overlap. Verification adds latency to knowledge of closure. With a missed event add the wait to a successful fallback scan, including timer accuracy and scheduling. Enforcement requires a safety timer. A starved fallback, an unreachable manager or a service that cannot stop leaves no demonstrated finite bound.

**Evidence.** The design and exposure model are untested. Only publish measured bounds with assumptions and recoverability evidence. Audit state changes, truncate the specified descriptor digest for correlation, and treat it as linkable data.
