# QMS Glossary

All major QMS-related terms used and/or defined across SOP-001 through SOP-007.

---

| Term | Definition | Source |
|------|------------|--------|
| **ADD (Addendum Report)** | Child document created to correct or supplement a closed executable document; must reference a CLOSED parent. | SOP-001 §3, SOP-004 §9B |
| **Administrator** | User group with all Initiator permissions plus administrative commands (e.g., fix). | SOP-001 §4.1 |
| **Adoption CR** | A Change Record that brings a new system from Genesis Sandbox into Production. | SOP-005 §3 |
| **Approval Gate** | System block on approval routing if any reviewer submitted request-updates; initiator must address changes and re-route for review. | SOP-001 §9.2 |
| **Archive** | Historical version storage at `.archive/{TYPE}/`; superseded versions are copied here with version suffix. | SOP-001 §7.3 |
| **Audit Trail** | Append-only event log stored in `.audit/` JSONL files; records all document lifecycle events. | SOP-001 §3, §5.3 |
| **CAPA (Corrective and Preventive Action)** | A category of execution item within an INV; not a standalone document. | SOP-003 §3, §6 |
| **CLOSED** | Terminal state for executable documents indicating execution is complete with no further action possible. | SOP-001 §8.3 |
| **Context** | Information passed to a subagent about the work to be performed. | SOP-007 §3 |
| **Controlled Document** | Any document managed under SOP-001. | SOP-001 §3 |
| **Corrective Action** | Action to eliminate the cause of an existing deviation and/or remediate the consequences of the deviation having occurred. | SOP-003 §3, §6.1 |
| **CR (Change Record)** | The controlled document authorizing a change; follows executable document workflow. | SOP-002 §3 |
| **Deviation** | Departure from approved procedure or expected product behavior. | SOP-003 §3 |
| **Draft** | A version under development, not yet approved. | SOP-001 §3 |
| **EFFECTIVE** | Status indicating a non-executable document is approved and in force. | SOP-001 §8.1 |
| **Editable Field** | A field in the executable block where execution work is recorded (e.g., execution details, evidence). | SOP-004 §3 |
| **ER (Exception Report)** | Child document for test execution failures within Test Protocols or Test Cases. | SOP-004 §9 |
| **Evidence** | Documentation proving completion of an execution item. | SOP-004 §3, §8 |
| **Executable Block** | Section of an executable document where implementation work is recorded; contains static and editable fields. | SOP-004 §3, §4 |
| **Executable Document** | A document that authorizes implementation activities (CR, INV, TP, ER, VAR, ADD, VR). | SOP-001 §3, SOP-004 §3 |
| **Execution Branch** | A git branch used during CR execution phase for implementing approved changes. | SOP-005 §3 |
| **Execution Item (EI)** | Discrete unit of work within the executable block; tracked in table format with task description, outcome, and signature. | SOP-004 §3, §4.2 |
| **Frontmatter** | Minimal YAML header in documents containing author-maintained fields (title, revision_summary). | SOP-001 §5.1 |
| **Genesis Sandbox** | A development environment for foundational work on new systems, outside QMS governance; uses `genesis/` branch pattern. | SOP-005 §3, §7.2 |
| **Inbox** | Per-user directory at `.claude/users/{username}/inbox/` containing task files for assigned reviews and approvals. | SOP-001 §12.2 |
| **Initiator** | User group that can create and manage documents through workflow. | SOP-001 §4.1 |
| **INV (Investigation)** | An executable document for analyzing deviations; contains root cause analysis and CAPAs. | SOP-003 §3 |
| **Merge Gate** | Prerequisites that must be met before code is merged to main: all tests pass (CI-verified), RS is EFFECTIVE, RTM is EFFECTIVE. | SOP-005 §7.1.3 |
| **Metadata** | Workflow state stored in `.meta/` sidecar JSON files; managed entirely by the QMS CLI. | SOP-001 §3, §5.2 |
| **Non-Executable Document** | A document that defines requirements or specifications (RS, RTM, SOP). | SOP-001 §3 |
| **Orchestrator** | The primary agent that spawns and coordinates subagents. | SOP-007 §3 |
| **Preventive Action** | Action to eliminate the cause of a potential future deviation; continuous improvement of the QMS. | SOP-003 §3, §6.1 |
| **Procedural Deviation** | A problem with a procedure as approved, or with the actual use of a procedure. | SOP-003 §3 |
| **Product Deviation** | A problem with the product itself (e.g., code bug, design flaw). | SOP-003 §3 |
| **QA (Quality Assurance Representative)** | Member of Quality group per SOP-001; mandatory reviewer and approver; assigns TUs to review teams. | SOP-002 §3, SOP-001 §4.1 |
| **Qualified Commit** | The git commit hash representing the code state under which a System Release was qualified; must be CI-verified. | SOP-005 §3, §7.1.2 |
| **Qualified State** | A system with approved RS, verified RTM, and code at a documented commit. | SOP-006 §3 |
| **Qualitative Proof** | Verification requiring intelligent judgment, documented as prose with code references; one of three RTM verification types. | SOP-006 §3, §6.2 |
| **Quality** | User group that assigns reviewers, reviews, and approves documents. | SOP-001 §4.1 |
| **Responsible User** | The user who has checked out a document and owns its workflow; persists through the revision cycle until approval. | SOP-001 §3, §5.2 |
| **RETIRED** | Terminal state indicating a document has been permanently archived and is no longer in use. | SOP-001 §8.3 |
| **Review Independence** | The principle that reviewers derive criteria from SOPs and their domain expertise, not from orchestrator instructions. | SOP-007 §3 |
| **Review Team** | QA plus any TUs assigned to a CR; remains consistent throughout the CR lifecycle. | SOP-002 §3 |
| **Reviewer** | User group that reviews and approves assigned documents. | SOP-001 §4.1 |
| **Root Cause** | Fundamental reason for a deviation. | SOP-003 §3 |
| **RS (Requirements Specification)** | SDLC document defining what a system shall do; contains requirements only. | SOP-006 §3, §5 |
| **RTM (Requirements Traceability Matrix)** | SDLC document mapping requirements to code and verification evidence; proof that requirements are met. | SOP-006 §3, §6 |
| **Scope Handoff** | Explicit specification of what the parent accomplished, what the child document absorbs, and confirmation no scope was lost. | SOP-004 §9A.5, §9B.5 |
| **Sidecar File** | JSON metadata file in `.meta/` managed by the QMS CLI; stores workflow state separate from document content. | SOP-001 §5.2 |
| **Static Field** | A field in the executable block that is defined at document creation and is never editable (e.g., test step instructions). | SOP-004 §3 |
| **Subagent** | A spawned agent assigned a specific role (e.g., Quality agent, Reviewer agent). | SOP-007 §3 |
| **System** | A distinct codebase governed under SOP-005 (e.g., a web application, a CLI tool). | SOP-005 §3 |
| **System Release** | A versioned, qualified state of a system's code; format `{SYSTEM}-{MAJOR}.{MINOR}`. | SOP-005 §3, §9 |
| **Task Outcome** | Pass or Fail designation for each execution item; Fail requires a VAR or ER attachment. | SOP-004 §4.2 |
| **Task Prompt** | The instruction provided when spawning a subagent. | SOP-007 §3 |
| **Terminal State** | A state from which no further transitions are possible (CLOSED, RETIRED). | SOP-001 §8.3 |
| **TP (Test Protocol)** | Optional child document of a CR detailing test procedures; follows its own executable workflow. | SOP-002 §3, §9 |
| **TU (Technical Unit)** | Member of Reviewer group per SOP-001; domain expert assigned by QA to review technical changes. | SOP-002 §3 |
| **Unit Test** | Automated, deterministic verification script; one of three RTM verification types. | SOP-006 §3, §6.2 |
| **VAR (Variance Report)** | Child document created when execution cannot proceed as planned; encapsulates resolution work for non-test executable documents. Type 1 requires full closure; Type 2 requires pre-approval to unblock parent. | SOP-001 §3, SOP-004 §9A |
| **Verification Record (VR)** | Pre-approved evidence form for structured behavioral verification; child of CR, VAR, or ADD; born IN_EXECUTION with no pre-review phase. | SOP-001 §3, SOP-004 §9C, SOP-006 §3 |
| **Workspace** | Per-user directory at `.claude/users/{username}/workspace/` containing documents checked out by that user. | SOP-001 §12.1 |
