# ScholarEdge — Security and Privacy

## Privacy principle

Research documents may contain unpublished work, academic records, proprietary material, or other sensitive information. The architecture should minimize unnecessary data transmission.

## Rules

- Store user documents locally by default.
- Do not commit sample private documents.
- Do not log document contents.
- Do not log API keys or authorization headers.
- Sanitize filenames and filesystem paths.
- Validate uploaded file types and sizes.
- Avoid path traversal.
- Delete derived data when a document is deleted.
- Keep external AI providers opt-in.

## External providers

If an external provider is supported:
- make it explicit in configuration/UI;
- clearly indicate that content leaves the device;
- never silently upload documents.

## Competition submissions

Do not include:
- private research papers;
- credentials;
- API keys;
- personal data;
- confidential employer information.

Remember that public repositories should be treated as public.
