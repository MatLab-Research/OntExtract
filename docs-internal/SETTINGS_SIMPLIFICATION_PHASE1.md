# Settings Simplification - Phase 1

**Date:** 2025-11-23
**Status:** Complete
**Branch:** development

## Overview

Simplified the OntExtract settings interface to reduce complexity and clarify access controls. The system now has clearer separation between admin and user concerns, and the LLM integration UI is more straightforward.

## Changes Made

### 1. Admin-Only Access Control

**File:** [app/routes/settings.py](../app/routes/settings.py:26-56)

**Changes:**
- Added admin check to settings route
- Non-admin users redirected to home with flash message
- Settings page now explicitly marked as "admin only" in docstring

**Impact:**
- Only administrators can access system-wide settings
- Regular users cannot modify processing defaults or system configuration
- Clearer security boundary

### 2. Simplified LLM Integration UI

**File:** [app/templates/settings/index.html](../app/templates/settings/index.html:58-143)

**Removed:**
- LLM Provider dropdown (was Anthropic/OpenAI)
- Model dropdown (was Claude 4.5, Claude 3.5, GPT-4, GPT-3.5)

**Added:**
- API key status banner (green success / yellow warning)
- Read-only provider display showing "Anthropic Claude (claude-sonnet-4-5-20250929)"
- Auto-disable toggle when API key not found
- Conditional Test Connection button (only shown when API key available)

**Kept:**
- Enable/Disable LLM Enhancement toggle
- Max Tokens configuration (100-4000, default 500)

**Rationale:**
- OntExtract only uses Claude (not OpenAI)
- Model selection is controlled in code (config/llm_config.py)
- Simplifies decision-making for users
- Maintains flexibility in backend for future changes

### 3. Navigation Update

**File:** [app/templates/base.html](../app/templates/base.html:283-294)

**Changes:**
- Settings menu item only visible to admin users
- Label changed to "Settings (Admin)" for clarity
- Non-admin users no longer see settings link in user dropdown

### 4. API Key Detection

**File:** [app/routes/settings.py](../app/routes/settings.py:48-50)

**Added:**
- Runtime check for ANTHROPIC_API_KEY environment variable
- Pass `api_key_available` flag to template
- Used to show/hide UI elements and enable/disable controls

### 5. JavaScript Updates

**File:** [app/templates/settings/index.html](../app/templates/settings/index.html:541-561)

**Changes:**
- `testLLMConnection()` function now hardcodes provider to 'anthropic'
- Removed dynamic provider selection (was reading from dropdown)
- Backend test endpoint still supports provider parameter for future use

## User Experience

### Before Phase 1:
- Settings accessible to all authenticated users
- Provider/Model dropdowns presented choices that weren't actually used
- No clear indication of API key status
- Configuration complexity suggested more flexibility than actually existed

### After Phase 1:
- Settings restricted to administrators
- Clear API key status with visual feedback (green/yellow banners)
- Simple on/off toggle for LLM features
- Provider/model shown as read-only information
- Test Connection button appears only when API key is available

## Technical Details

### Settings Storage Model

The `AppSetting` model supports both global and user-specific settings:
- **Global settings:** `user_id = NULL`
- **User-specific:** `user_id = <user_id>`

Current implementation saves all settings as user-specific (line 511 in index.html sets `user_specific: true`).

**Note:** For future enhancement, could change admin settings to be global (system-wide) and user settings to be per-user overrides.

### Current User Roles

From database check (2025-11-23):
- **Admin users:** chris, wook, methods_tester
- **Regular users:** test_user, demo_researcher, system, demo

Admin status is checked via `current_user.is_admin` (User model field: [app/models/user.py:38](../app/models/user.py:38))

### LLM Configuration Location

Provider and model selection moved to code-level configuration:
- Primary config: [config/llm_config.py](../config/llm_config.py)
- Orchestration nodes: [app/orchestration/nodes.py](../app/orchestration/nodes.py)

This allows technical users to change models without exposing complexity in UI.

## Testing

### Manual Testing Checklist

1. **Admin User Access:**
   - Login as admin user (chris, wook, or methods_tester)
   - Verify "Settings (Admin)" appears in user dropdown
   - Access `/settings/` successfully
   - See all tabs (LLM, Processing, NLP, Prompt Templates)

2. **Non-Admin User Access:**
   - Login as regular user (test_user or demo)
   - Verify NO "Settings" link in user dropdown
   - Direct access to `/settings/` redirects to home with error message

3. **API Key Status:**
   - With ANTHROPIC_API_KEY set: Green banner, toggle enabled, Test Connection visible
   - Without API key: Yellow banner, toggle disabled, Test Connection hidden

4. **LLM Settings:**
   - Provider shown as read-only "Anthropic Claude"
   - Model shown as read-only "claude-sonnet-4-5-20250929"
   - Toggle and Max Tokens functional
   - Save Changes updates settings

5. **Other Tabs:**
   - Processing, NLP, Prompt Templates unchanged
   - All functionality preserved

## Files Modified

1. [app/routes/settings.py](../app/routes/settings.py) - Admin check, API key detection
2. [app/templates/settings/index.html](../app/templates/settings/index.html) - Simplified LLM UI, updated JavaScript
3. [app/templates/base.html](../app/templates/base.html) - Admin-only navigation
4. [docs/SETTINGS_SIMPLIFICATION_PHASE1.md](SETTINGS_SIMPLIFICATION_PHASE1.md) - This document

## Next Steps (Future Phases)

### Phase 2 - Role-Based Access (Optional)

1. Create user preferences page (`/profile` or `/preferences`)
2. Move user-specific settings out of admin settings
3. Add `user_id` column to `PromptTemplate` for personal templates
4. Allow users to copy and customize global templates

### Phase 3 - Future Extensibility (Post-JCDL)

1. If local models needed: Re-add provider selection (admin-only)
2. If multiple Claude models: Re-add model dropdown (admin-only)
3. Keep user experience simple: "Use LLM Enhancement: Yes/No"
4. Advanced configuration remains in admin settings

## Backwards Compatibility

### Database Changes: None
- No schema changes required
- Existing settings continue to work
- No migration needed

### Configuration Changes: None
- Environment variables unchanged
- LLM configuration preserved in code
- API endpoints unchanged

### Breaking Changes: None
- Existing workflows unaffected
- LLM functionality identical
- Only UI simplified

## Benefits

1. **Clearer Security:** Admin-only access prevents accidental system configuration changes
2. **Simpler UX:** Users see only relevant controls (on/off toggle)
3. **Better Feedback:** API key status immediately visible
4. **Future-Proof:** Backend retains flexibility for provider/model changes
5. **Reduced Confusion:** No unused options presented to users

## Risks & Mitigations

### Risk: Admin users need clear designation
**Mitigation:** Database shows 3 admin users; can promote others via SQL if needed

### Risk: Regular users may want some settings
**Mitigation:** Phase 2 will add user preferences page for personal settings

### Risk: Future provider/model changes require code edits
**Mitigation:** Config files well-documented; admin users can edit if needed

---

**Implementation Date:** 2025-11-23
**Implemented By:** Claude Code (Session 24 continuation)
**Testing Status:** Manual testing required (see checklist above)
**Production Status:** Ready for testing on localhost:8765
