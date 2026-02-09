# UI/UX Design for Contest Creation Feature

## Overview

This document describes the user interface and user experience for the contest creation and management feature.

## User Roles

### Students
- Can view published contests
- Can participate in contests
- **Cannot** create or modify contests

### Course Teachers
- Course owner and additional teachers assigned to the course
- Can view all contests in their courses (including drafts)
- Can create new contests
- Can add/remove problems to/from contests
- Can configure contest settings

## Page Layouts

### 1. Course Page (Updated)

```
┌─────────────────────────────────────────────────────────┐
│  Booml Header                                    [Login] │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  [Course Title]                      [Create Contest]    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Contests                                        │    │
│  ├─────────────────────────────────────────────────┤    │
│  │  → Contest 1                                     │    │
│  │  → Contest 2                                     │    │
│  │  → Contest 3 (Draft) [only visible to teachers] │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  This course has no contests yet. [if empty]             │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**New Elements**:
- "Create Contest" button (top-right, primary color, visible only to teachers)
- Draft indicators on contest items

### 2. Contest Creation Dialog

```
┌─────────────────────────────────────────────────────────┐
│  Создать контест                                     [×] │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Название контеста *                                     │
│  [_____________________________________________]          │
│                                                           │
│  Описание                                                │
│  [_____________________________________________]          │
│  [_____________________________________________]          │
│  [_____________________________________________]          │
│  [_____________________________________________]          │
│                                                           │
│  Система оценки                                          │
│  [IOI (сумма баллов)           ▼]                        │
│                                                           │
│  ☐ Опубликовать контест     ☐ Рейтинговый контест       │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                                     [Отмена]  [Создать]  │
└─────────────────────────────────────────────────────────┘
```

**Features**:
- Required field indicator (*)
- Multi-line description field
- Dropdown for scoring system
- Checkboxes for flags
- Validation (title required)
- Error message area

### 3. Contest Page (Updated)

```
┌─────────────────────────────────────────────────────────┐
│  Booml Header                                    [Login] │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Contest Title                                           │
│                                                           │
│                     [Add Problem] [Leaderboard]          │
│                                                           │
│  Contest description appears here...                     │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Problems                                        │    │
│  ├─────────────────────────────────────────────────┤    │
│  │  → Problem 1: Linear Regression                  │    │
│  │  → Problem 2: Classification                     │    │
│  │  → Problem 3: Neural Networks                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  This contest has no problems yet. [if empty]            │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**New Elements**:
- "Add Problem" button (visible only to teachers)
- Contest description box
- Empty state message

### 4. Add Problem Dialog

```
┌─────────────────────────────────────────────────────────┐
│  Добавить задачу в контест                           [×] │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Linear Regression Basics                    ✓  │    │
│  │  Рейтинг: 800  ● Опубликована                   │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Gradient Descent Implementation                │    │
│  │  Рейтинг: 1200  ○ Черновик                      │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Neural Network Classification                  │    │
│  │  Рейтинг: 1600  ● Опубликована                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  У вас нет задач. Создайте задачу в Полигоне.           │
│  [if no problems available]                              │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                                     [Отмена]  [Добавить] │
└─────────────────────────────────────────────────────────┘
```

**Features**:
- List of available problems
- Problem metadata display (rating, status)
- Visual selection (highlighted + checkmark)
- Click to select
- Empty state with link to Polygon
- Filters out problems already in contest

## Visual Design Details

### Color Scheme
- Primary action buttons: `var(--color-primary)` (blue)
- Secondary buttons: `var(--color-button-secondary)` (light gray)
- Success indicators: `var(--color-success)` (green)
- Draft/unpublished: `var(--color-text-muted)` (gray)
- Error messages: Red background with darker red text

### Typography
- Page titles: 28px, weight 600
- Dialog titles: 20px, weight 600
- Form labels: 14px, weight 500
- Button text: 16px, weight 500
- Body text: 15px, regular

### Spacing
- Dialog padding: 24px
- Form field gaps: 16px
- Button gaps: 12px
- Section gaps: 12px

### Interactive Elements

#### Buttons
- Border radius: 8px
- Padding: 10px 16px
- Hover: slight brightness change
- Disabled: reduced opacity

#### Form Inputs
- Border radius: 8px
- Padding: 10px 12px
- Border: 1px solid (default)
- Focus: primary color border

#### Problem Items
- Border radius: 10px
- Border: 2px solid
- Hover: primary color border
- Selected: primary color border + light background
- Checkmark: 24px, primary color

### Responsive Design

#### Desktop (> 900px)
- Content max-width: 960px
- Padding: 28px 24px
- Two-column form layouts where applicable

#### Mobile (< 900px)
- Content padding: 24px 16px
- Single-column layouts
- Full-width buttons
- Dialog max-width: 100% - 32px

## Accessibility

### Keyboard Navigation
- All buttons are focusable
- Enter key submits forms
- Escape key closes dialogs
- Tab order follows visual layout

### Screen Readers
- Proper label associations
- Button text describes action
- Error messages linked to fields
- Status indicators have text alternatives

### Visual Indicators
- Focus outlines: 2px solid
- Error states: red borders + icon
- Success states: green checkmark
- Loading states: "Loading..." text

## User Flows

### Flow 1: Creating a Contest

1. Teacher navigates to course page
2. Sees "Create Contest" button
3. Clicks button
4. Dialog opens with focus on title field
5. Enters contest title (required)
6. Optionally enters description
7. Selects scoring system from dropdown
8. Checks "Published" if ready to publish
9. Checks "Rated" if contest affects ratings
10. Clicks "Create"
11. Dialog shows loading state
12. On success: navigates to new contest page
13. On error: shows error message in dialog

### Flow 2: Adding Problems

1. Teacher navigates to contest page
2. Sees "Add Problem" button
3. Clicks button
4. Dialog opens showing available problems
5. Clicks on a problem to select it
6. Problem highlights with checkmark
7. Clicks "Add"
8. Dialog shows loading state
9. On success: dialog closes, page reloads with new problem
10. On error: shows error message in dialog

## Error Handling

### Validation Errors
- Title required: "Название контеста обязательно"
- Empty problem list: Link to Polygon to create problems
- Network errors: "Не удалось создать контест" / "Не удалось добавить задачу"

### Error Display
- Red background box
- Clear, user-friendly message in Russian
- Positioned below form fields
- Dismisses on retry

## Loading States

### Contest Creation
- Button text changes: "Создать" → "Создание..."
- Button disabled during loading
- Prevents double-submission

### Problem Addition
- Button text changes: "Добавить" → "Добавление..."
- Button disabled during loading
- Prevents double-submission

### Problem List Loading
- Shows: "Загрузка задач..."
- Centered in dialog body
- Minimum height to prevent layout shift

## Empty States

### No Contests
```
This course has no contests yet.
```

### No Problems in Contest
```
This contest has no problems yet.
```

### No Available Problems
```
У вас нет задач. Создайте задачу в [Полигоне].
```
- Includes link to Polygon
- Encourages action
