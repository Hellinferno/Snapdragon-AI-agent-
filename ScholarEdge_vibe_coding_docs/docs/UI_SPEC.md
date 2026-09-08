# ScholarEdge — UI Specification

## Primary layout

The application should feel like a focused research workspace rather than a generic chatbot.

### Main navigation
- Library
- Research
- Learn
- Compare
- Vision (when implemented)

### Main workspace
- document/library panel
- conversation/research workspace
- source/evidence panel

## Core screens

### Library
Users can:
- upload documents;
- view processing status;
- organize collections;
- open a document.

### Research
Users can:
- ask questions;
- select document scope;
- inspect citations;
- open source pages.

### Compare
Users can:
- select multiple papers;
- choose comparison dimensions;
- inspect structured results.

### Learn
Users can:
- request explanations;
- generate quizzes;
- generate flashcards later.

## Trust UI

Source information should be visually distinct from generated text.

Every grounded answer should make it easy to identify:
- source document;
- page;
- relevant excerpt when appropriate.

If retrieval fails, show an explicit insufficient-evidence state.

## UI constraints

- Do not add decorative features that reduce research usability.
- Avoid dense nested cards.
- Preserve readable typography.
- Make source navigation fast.
- Design for a laptop viewport first.
- Keep accessibility in mind from the beginning.
