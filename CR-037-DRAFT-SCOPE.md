# CR-037 Draft Scope: Production pipe-dream Cleanup

This document records discrepancies found during CR-036 that need to be addressed in the production pipe-dream repository.

## Overview

During CR-036 (qms-cli initialization and bootstrapping), we discovered discrepancies between the qualified code/RS and the documentation (SOPs, README, agent files). These discrepancies were fixed in the qms-cli dev branch but still exist in production pipe-dream.

---

## Category 1: Document Types

### Issue
The following document types are referenced in documentation but do not exist in the code:
- **CAPA** - Listed in README and SOPs but not in `DOCUMENT_TYPES`
- **OQ, CS, DS** - Referenced in SOP-006 but not functional

### Actual Document Types (from code)
```
SOP, CR, INV, TP, ER, VAR, TEMPLATE + SDLC namespace RS/RTM
```

### Files to Fix
- `QMS/SOP/SOP-001.md` - Document Naming Convention table
- `QMS/SOP/SOP-006.md` - References to OQ/CS/DS
- Any other documentation referencing non-existent types

---

## Category 2: User Groups and Permissions

### Issue
The README User Groups table had incorrect information:
- Listed specific members instead of describing group capabilities
- Claimed `quality` group can use `fix` command
- `fix` command is actually hardcoded to usernames `{"qa", "lead"}` only

### RS Discrepancy
REQ-SEC-002 states administrator group gets `fix`, but code hardcodes specific users.

**Options for resolution:**
1. Fix the code to honor group permissions (code change, separate CR)
2. Update the RS to reflect the actual restriction
3. Document as intentional design (fix is sensitive, limited to specific users)

### Files to Fix
- `README.md` - User Groups section
- Potentially RS if we decide to align documentation with code behavior

---

## Category 3: Hardcoded User References

### Issue
SOPs and README contained hardcoded usernames that should be generic:
- `tu_ui`, `tu_scene`, `tu_sketch`, `tu_sim`, `bu`
- `reviewer1`, `reviewer2`, `reviewer3`, `reviewer4`

These are project-specific users, not generic examples.

### Files to Fix
- `QMS/SOP/SOP-001.md` - Directory structure, command examples
- `QMS/SOP/SOP-007.md` - Scope section, definitions table
- `README.md` - Workflow examples

---

## Category 4: Agent Files

### Issue
Agent files in production may lack proper `group:` frontmatter.

### Files to Check
- `.claude/agents/qa.md`
- `.claude/agents/tu_ui.md`
- `.claude/agents/tu_scene.md`
- `.claude/agents/tu_sketch.md`
- `.claude/agents/tu_sim.md`
- `.claude/agents/bu.md`

---

## Verification Checklist

After CR-037 implementation:
- [ ] Grep for CAPA, OQ, CS, DS - should find no functional references
- [ ] Grep for reviewer1, reviewer2, etc. - should find no hardcoded examples
- [ ] Grep for tu_ui, tu_scene outside agent files - should find no hardcoded examples
- [ ] All agent files have valid `group:` frontmatter
- [ ] README User Groups matches code in qms_config.py

---

## Notes

This cleanup was identified during CR-036 execution. The fixes were applied to the qms-cli dev branch seed documents so that new projects initialized via `qms init` receive consistent documentation.

Production pipe-dream requires a separate CR (CR-037) because those documents are QMS-controlled.
