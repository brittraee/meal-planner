# Recipe Card Format

All recipe files in `Meals/` follow this structure. The parser reads
title, ingredients, quick prep, and tags. Fields after tags are for
display only.

## Filename

`NN_Recipe_Title.md` — zero-padded number, underscores for spaces.

## Template

```markdown
### Recipe Title
**Main Ingredients:**
- Ingredient 1
- Ingredient 2
- Optional: Ingredient 3

**Quick Prep:**
1-2 sentence summary of the core technique or first step.

**Tags:** #protein #cuisine #XXmin

**Prep Time:** XX min | **Total Time:** XX min

**Instructions:**
**Step 1**
First step of the recipe.

**Step 2**
Second step of the recipe.
```

## Field Rules

| Field | Required | Parser reads? | Notes |
|-------|----------|---------------|-------|
| Title | Yes | Yes | `### ` prefix, plain text |
| Main Ingredients | Yes | Yes | 4-10 items, bullet list, two trailing spaces per line |
| Quick Prep | Yes | Yes | 1-2 sentences; sits between ingredients and tags |
| Tags | Yes | Yes | Space-separated `#tags` on one line |
| Prep Time / Total Time | Yes | No | `XX min` rounded to nearest 5 |
| Instructions | Yes | No | Full steps; use `**Step N**` headers |

## Tag Conventions

**Protein** (pick one):
`#chicken` `#beef` `#pork` `#shrimp` `#seafood` `#fish` `#lamb` `#vegetarian`

**Cuisine** (pick one):
`#american` `#mexican` `#italian` `#thai` `#chinese` `#indian` `#japanese`
`#british` `#french` `#korean` `#vietnamese` `#greek` `#cajun` `#jamaican`

**Diet** (only if applicable):
`#paleo` `#keto`

**Time** (total time, rounded to nearest 5):
`#30min` `#45min` `#60min` `#90min` `#120min` etc.

## Ingredient Formatting

- Plain name: `- Chicken Breast` → parsed as required
- Optional: `- Optional: sour cream` → parsed with `optional=True`
- Alternatives: `- Ground beef or turkey` → parsed with alternatives
- Keep to common pantry names the normalizer recognizes

## Quick Prep Tips

- Should read as a standalone summary (shown on recipe cards)
- Pull from the first or most distinctive step
- Keep under ~30 words
