---
title: 'Standard Operating Procedure Template'
revision_summary: 'CR-017: Initial migration to QMS control'
---

<!--
================================================================================
TEMPLATE DOCUMENT NOTICE
================================================================================
This template is a QMS-controlled document. The frontmatter contains only:
- title: Document title
- revision_summary: Description of changes in this revision

All other metadata (version, status, responsible_user, dates) is managed
automatically by the QMS CLI in sidecar files (.meta/) per SOP-001 Section 5.

When creating an SOP from this template, copy from the EXAMPLE FRONTMATTER onward.
================================================================================
-->

---
title: '{{TITLE}}'
revision_summary: 'Initial creation'
---

<!--
================================================================================
TEMPLATE USAGE GUIDE
================================================================================

DOCUMENT TYPE:
SOPs are NON-EXECUTABLE documents. They define procedures but do not authorize
implementation activities.

WORKFLOW:
  DRAFT -> IN_REVIEW -> REVIEWED -> IN_APPROVAL -> APPROVED -> EFFECTIVE

PLACEHOLDER TYPES:
1. {{DOUBLE_CURLY}} - Replace when drafting the SOP

After authoring:
- NO {{...}} placeholders should remain

ID FORMAT:
  SOP-NNN
  Example: SOP-001, SOP-006

STANDARD STRUCTURE:
1. Purpose       - Why this procedure exists
2. Scope         - What it covers and what it doesn't
3. Definitions   - Terms specific to this procedure
4. [Content]     - The actual procedure (sections 4+)
N. References    - Related documents

Delete this comment block after reading.
================================================================================
-->

# SOP-XXX: {{TITLE}}

## 1. Purpose

{{PURPOSE - What does this procedure establish? What problem does it solve?}}

---

## 2. Scope

This SOP applies to {{SCOPE - Who/what is governed by this procedure}}:

- {{Item 1}}
- {{Item 2}}
- {{Item 3}}

**Out of Scope:**

- {{Exclusion 1}}
- {{Exclusion 2}}

---

## 3. Definitions

| Term | Definition |
|------|------------|
| **{{Term 1}}** | {{Definition 1}} |
| **{{Term 2}}** | {{Definition 2}} |
| **{{Term 3}}** | {{Definition 3}} |

---

## 4. {{FIRST_CONTENT_SECTION_TITLE}}

{{CONTENT - Begin the actual procedure here. Number sections sequentially.}}

### 4.1 {{Subsection Title}}

{{Subsection content}}

### 4.2 {{Subsection Title}}

{{Subsection content}}

---

## 5. {{SECOND_CONTENT_SECTION_TITLE}}

{{Continue with additional sections as needed. Adjust section numbers accordingly.}}

---

## N. References

{{REFERENCES - List related documents}}

| Document | Relationship |
|----------|--------------|
| SOP-001 | Document control lifecycle |
| {{DOC_ID}} | {{Relationship description}} |

---

**END OF DOCUMENT**
