# AWS SES Support Case Body (Sanitized)

## Subject

Amazon SES `SendEmail` returns HTTP 403 `AccessDenied` while IAM Policy
Simulator returns Explicit Allow in `ap-northeast-1`

## Case body

We are investigating a bounded, synthetic-only Amazon SES API request from an
IAM user in `ap-northeast-1` (Tokyo). The request used AWS SDK for Java v2
`SesClient.sendEmail` through our production request factory. It contained one
verified sender identity, exactly one verified synthetic To recipient, no CC,
no BCC, no Reply-To, no Return-Path, no tags, no configuration set, no
delegated-sending fields, and no retry.

The latest request was rejected by Amazon SES with `HTTP 403 AccessDenied`.
Exactly one request was made; no MessageId or delivery confirmation was
returned. No IAM, SES, account, or resource mutation occurred. The request was
synthetic and carried no customer or business data.

The attached IAM design is one customer inline `Allow` statement for
`ses:SendEmail` and `ses:SendRawEmail` on the exact verified SES identity
resource in `ap-northeast-1`, constrained by:

- exact `ses:FromAddress`;
- `ForAllValues:StringEquals` on one `ses:Recipients` value; and
- `aws:SecureTransport=true`.

IAM Policy Simulator was run for the intended action, exact identity resource,
expected FromAddress, expected Recipients, and `SecureTransport=true`. It
returned `ALLOWED / EXPLICIT ALLOW`.

Read-only Console checks show the Tokyo SES account is healthy but still in the
sandbox, the sender and synthetic recipient identities are verified, there is
no permissions boundary or group policy, the account is not in AWS
Organizations, and no sending pause, suppression entry, or reputation block is
visible. The configured AWS profile resolves to the intended validation user.

Please investigate the service-side authorization decision for the rejected
request and explain why the simulator result differs from the live SES result.
We are not requesting broader permissions, sandbox removal, or any account or
provider mutation.

## Requested questions

1. Why can this same-account `SendEmail` request receive HTTP 403
   `AccessDenied` when IAM Policy Simulator evaluates the intended exact
   action/resource/condition context as Explicit Allow?
2. Is there an Amazon SES authorization or account layer in
   `ap-northeast-1` that can reject this request but is not represented by IAM
   Policy Simulator?
3. Does SES derive `ses:FromAddress` or `ses:Recipients` differently from the
   `Source` and `Destination` values of `SendEmail` in any relevant case?
4. Does same-account sending from an owned verified identity require any
   additional identity-level authorization not described by the standard IAM
   `SendEmail` resource model?
5. Can Support inspect service-side authorization records for the UTC
   execution window listed in the appendix even though the application did not
   retain the full request ID?
6. If a request ID is strictly required, what is the minimum safe correlation
   metadata needed for a future separately approved diagnostic?

Historical local and provider outcomes are preserved in the technical appendix.
No additional send is requested by this case.
