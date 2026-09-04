# Changelog — contracts

Versionamento semântico dos eventos Kafka compartilhados do monorepo
`conference-back` (Princípio IV da constituição).

## [1.0.0] - 2026-09-03

### Added

- `CheckoutIniciado` (v1.0): evento informativo publicado pelo serviço de checkout
  ao criar uma sessão de checkout (feature
  [001-iniciar-checkout](../../specs/001-iniciar-checkout/spec.md)).
  Campos: `event_type`, `event_version`, `saga_id`, `session_id`, `cart_id`,
  `total`, `expires_at`, `occurred_at`. Schema em
  `specs/001-iniciar-checkout/contracts/events/checkout-iniciado.schema.json`.
