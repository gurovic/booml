# Contest Creation Feature Implementation

## Overview

This document describes the implementation of the contest creation and management feature for teachers in the Booml platform.

## Feature Description

Teachers (section owners) can now:
1. Create contests within their courses
2. Add problems from their polygon to contests
3. Configure contest settings (scoring, publication, rating status)

## Implementation Details

### Backend Changes

#### 1. Course Detail API Enhancement
**File**: `backend/runner/views/course.py`

Added `section_owner_id` field to the course detail response to enable frontend access control:

```python
return JsonResponse({
    "id": course.id,
    "title": course.title,
    "description": course.description,
    "section": course.section_id,
    "section_title": course.section.title,
    "section_owner_id": course.section.owner_id,  # NEW
    "participants": participants,
})
```

#### 2. Contest Detail API Enhancement
**File**: `backend/runner/views/contest_draft.py`

Added ownership information to contest detail response:

```python
return JsonResponse({
    # ... existing fields ...
    "is_owner": is_owner,                          # NEW
    "section_owner_id": contest.course.section.owner_id,  # NEW
})
```

#### 3. Existing Endpoints Utilized
- `POST /contest/{course_id}/new/` - Create contest (already existed)
- `POST /contest/{contest_id}/problems/add/` - Add problem to contest (already existed)
- `GET /backend/polygon/problems` - List user's problems (already existed)

### Frontend Changes

#### 1. Contest API Client
**File**: `frontend/src/api/real/contest.js`

Added new methods:
```javascript
export async function createContest(courseId, contestData)
export async function addProblemToContest(contestId, problemId)
```

#### 2. Course Page Updates
**File**: `frontend/src/pages/CoursePage.vue`

**New Features**:
- "Create Contest" button (visible only to section owners)
- Contest creation dialog with fields:
  - Title (required)
  - Description (optional)
  - Scoring system dropdown (IOI/ICPC/Partial)
  - "Published" checkbox
  - "Rated" checkbox
- Form validation and error handling
- Navigation to newly created contest

**Access Control**:
```javascript
const canCreateContest = computed(() => {
  if (!userStore.currentUser || !course.value) return false
  return course.value.section_owner_id === userStore.currentUser.id
})
```

#### 3. Contest Page Updates
**File**: `frontend/src/pages/ContestPage.vue`

**New Features**:
- "Add Problem" button (visible only to section owners)
- Problem selection dialog that:
  - Lists available problems from user's polygon
  - Shows problem metadata (rating, published status)
  - Filters out problems already in contest
  - Visual selection UI with checkmarks
- Contest description display
- Automatic reload after adding problems

**Access Control**:
```javascript
const canManageContest = computed(() => {
  if (!userStore.currentUser || !contest.value) return false
  return contest.value.section_owner_id === userStore.currentUser.id
})
```

#### 4. Mock API Updates
**Files**: `frontend/src/api/mock/contest.js`, `frontend/src/api/mock/course.js`

Added mock implementations for:
- `createContest()`
- `addProblemToContest()`
- `section_owner_id` field in course response

## User Experience Flow

### Creating a Contest

1. Teacher navigates to a course page
2. Sees "Create Contest" button (if they are the section owner)
3. Clicks button to open creation dialog
4. Fills in contest details:
   - Required: Title
   - Optional: Description, scoring type, publication status, rating status
5. Clicks "Create" button
6. System creates contest and navigates to contest page

### Adding Problems to Contest

1. Teacher navigates to their contest page
2. Sees "Add Problem" button (if they are the section owner)
3. Clicks button to open problem selection dialog
4. Sees list of their problems from polygon
5. Selects a problem by clicking on it
6. Clicks "Add" button
7. Problem is added to contest and page reloads

## Design Patterns

### Consistent Modal Dialogs
- Overlay with click-to-close
- Header with title and close button
- Body with form fields
- Footer with Cancel/Confirm buttons
- Error message display area

### Access Control Pattern
- Backend: Check `course.section.owner_id == request.user.id`
- Frontend: Check `section_owner_id === currentUser.id`
- Progressive enhancement: buttons only appear for authorized users

### Styling
- Uses existing CSS variables for colors
- Matches site's design system
- Responsive layout
- Smooth transitions and hover effects

## Security Considerations

1. **Backend Authorization**: All contest creation/modification endpoints check that the user is the section owner
2. **Frontend UI**: Buttons are conditionally rendered based on ownership
3. **API Validation**: Backend validates all input fields before creating/modifying contests
4. **CSRF Protection**: All POST requests include CSRF tokens

## Testing

### Code Validation
- ✅ Python backend code compiles without errors
- ✅ Frontend code passes ESLint validation
- ✅ Existing backend tests still pass (no breaking changes)

### Manual Testing Required
- [ ] Test contest creation as section owner
- [ ] Test contest creation fails for non-owners
- [ ] Test problem addition to contest
- [ ] Test UI responsiveness on mobile/desktop
- [ ] Test error handling scenarios

## Future Enhancements

1. **Contest Editing**: Add ability to edit contest details after creation
2. **Problem Removal**: Add ability to remove problems from contests
3. **Bulk Problem Addition**: Allow adding multiple problems at once
4. **Contest Templates**: Save contest configurations as templates
5. **Contest Cloning**: Duplicate existing contests

## Files Modified

### Backend
- `backend/runner/views/course.py`
- `backend/runner/views/contest_draft.py`

### Frontend
- `frontend/src/api/real/contest.js`
- `frontend/src/api/polygon.js`
- `frontend/src/pages/CoursePage.vue`
- `frontend/src/pages/ContestPage.vue`
- `frontend/src/api/mock/contest.js`
- `frontend/src/api/mock/course.js`

## Dependencies

No new dependencies were added. The implementation uses:
- Existing Vue 3 composition API
- Existing API client infrastructure
- Existing CSS variable system
- Existing authentication/authorization system
