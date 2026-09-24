# Testing Guide: Last Updated Time Enhancement

## Quick Start

### Build & Deploy
```bash
# Using Docker Compose
docker-compose up --build

# Or manually
cd frontend
npm install
npm run build

# Docker build
docker build -t newscollectbot-frontend:latest .
docker run -p 3000:80 newscollectbot-frontend:latest
```

Then visit: http://localhost:3000

---

## Visual Testing Checklist

### ✅ Desktop Display (1024px+)
- [ ] Refresh button visible with 🔄 icon and "Refresh News" text
- [ ] Last updated badge appears next to button (should see ✓ icon + time text)
- [ ] Badge has rounded corners and light background
- [ ] 8px visible gap between button and badge
- [ ] Badge shows "Just now", "2m ago", "1h ago", "3d ago" format
- [ ] Icon has subtle pulse/glow animation (especially for "Just now")

### ✅ Badge Styling
- [ ] **Fresh (< 12 hours):** Green color, ✓ icon, badge has glow animation
- [ ] **Stale (12-24 hours):** Yellow/amber color, ! icon, no animation
- [ ] **Very Stale (> 24 hours):** Red color, ! icon, no animation

### ✅ Hover Effects
- [ ] Hover over badge → background brightens
- [ ] Hover over badge → subtle lift (moves up ~1px)
- [ ] Hover over badge → border appears around badge
- [ ] Hover over badge → shadow appears beneath
- [ ] Cursor changes to "help" cursor (?) when hovering
- [ ] Tooltip appears showing full timestamp (e.g., "Last updated: 1/15/2024, 2:30:45 PM")

### ✅ Real-Time Updates
- [ ] Badge updates every second without page reload
- [ ] "Just now" → "1s ago" → "2s ago" (immediately visible)
- [ ] After 60 seconds, switches to "1m ago"
- [ ] After 60 minutes, switches to "1h ago"
- [ ] After 24 hours, color changes to yellow
- [ ] After 48 hours, color changes to red
- [ ] Time values are always accurate relative to current time

### ✅ Refresh Action
1. Click "🔄 Refresh News" button
   - [ ] Badge disappears immediately
   - [ ] Button shows spinner icon
   - [ ] Button text changes to "Fetching..."
   - [ ] Progress bar appears below button
   - [ ] Progress bar animates smoothly from 0 to ~97%

2. After refresh completes:
   - [ ] Progress bar completes to 100%
   - [ ] Progress bar fades out
   - [ ] Badge reappears with animation
   - [ ] Badge shows "Just now" with fresh green styling
   - [ ] Icon has pulse/glow animation

### ✅ Mobile View (<768px)
- [ ] Badge stacks **below** refresh button (vertical layout)
- [ ] Button takes full width
- [ ] Badge takes full width with smaller font (11px)
- [ ] Badge still shows same information but more compact
- [ ] Touch target is adequately large (40px+ height)
- [ ] All styling still visible on small screens
- [ ] Hover effects still work on touch-capable devices (or tap equivalent)

### ✅ Dark Mode (if applicable)
- [ ] Badge colors visible against dark background
- [ ] Text contrast meets accessibility standards
- [ ] Animation still visible in dark mode
- [ ] Border/shadow effects visible in dark mode

---

## Interactive Testing

### Scenario 1: Just Refreshed
```
Expected state:
- Badge shows "Just now"
- Green color, ✓ icon
- Icon has pulsing glow animation
- Hover tooltip shows current timestamp
```

### Scenario 2: Wait 30 seconds
```
Expected state (after 30s):
- Badge shows "30s ago"
- Still green, ✓ icon
- Still has glow animation
- Tooltip still shows accurate timestamp
```

### Scenario 3: Wait until 61 seconds
```
Expected state (at 1:01):
- Badge shows "1m ago"
- Color and styling unchanged
- Updates transition smoothly
```

### Scenario 4: Force 12-hour old timestamp (browser dev tools)
```
Steps:
1. Open browser DevTools (F12)
2. Open Console tab
3. Run: localStorage.setItem('lastRefreshTime', String(Date.now() - 12 * 3600 * 1000))
4. Refresh page

Expected state:
- Badge shows "12h ago" or similar
- Color changes to YELLOW (⚠)
- Icon shows "!"
- Glow animation is gone
```

### Scenario 5: Force 25-hour old timestamp
```
Steps:
1. Open browser DevTools (F12)
2. Open Console tab
3. Run: localStorage.setItem('lastRefreshTime', String(Date.now() - 25 * 3600 * 1000))
4. Refresh page

Expected state:
- Badge shows "1d ago"
- Color changes to RED
- Icon shows "!"
- Glow animation is gone
- Consider clicking Refresh News to get green status back
```

### Scenario 6: Clear timestamp
```
Steps:
1. Open DevTools Console
2. Run: localStorage.removeItem('lastRefreshTime')
3. Refresh page

Expected state:
- Badge disappears (doesn't show)
- Only shows after first refresh
```

---

## Responsive Testing

### Test on Different Breakpoints

#### Desktop (1440px)
```bash
# Chrome DevTools → Responsive Design Mode
# Set to 1440 x 900
# Expected: Horizontal layout, full spacing
```

#### Tablet (768px)
```bash
# Chrome DevTools → iPad responsive
# Expected: May wrap, standard styling
```

#### Mobile (375px - iPhone SE)
```bash
# Chrome DevTools → iPhone SE responsive
# Expected: Vertical stack, full-width elements, smaller fonts
```

#### Mobile (414px - iPhone 12 Pro)
```bash
# Chrome DevTools → iPhone 12 Pro responsive
# Expected: Vertical stack, comfortable spacing
```

---

## Animation Testing

### Check Glow Animation
```javascript
// Run in browser console (only for fresh data)
const icon = document.querySelector('.refresh-icon');
// Should see continuous pulsing effect
// Watch the icon - it should have a subtle glow that appears and fades
```

### Verify Animation Performance
```javascript
// Check frame rate while animation plays
// Open DevTools → Performance tab
// Record 3-5 seconds while looking at badge
// Should maintain 60 FPS, no jank
```

---

## Accessibility Testing

### Keyboard Navigation
- [ ] Tab to badge → visible focus indicator
- [ ] Badge receives hover effects on tab focus
- [ ] Tooltip appears when focused (accessibility feature)

### Screen Reader Testing (NVDA/JAWS on Windows, VoiceOver on Mac)
- [ ] Badge is announced as interactive element
- [ ] Tooltip text is read aloud when focused
- [ ] Color-coded status is supplemented with icon (not color-only)

### Color Contrast
- [ ] Use Chrome DevTools → Accessibility inspector
- [ ] Check contrast ratios:
  - [ ] Green badge text: 4.5:1 minimum (WCAG AA)
  - [ ] Yellow badge text: 4.5:1 minimum
  - [ ] Red badge text: 4.5:1 minimum

---

## Edge Cases

### Test These Scenarios

1. **Very fast refresh** (spam click Refresh News button)
   - [ ] Doesn't break UI
   - [ ] Progress bar resets correctly
   - [ ] Timestamp updates after each refresh

2. **Network lag simulation** (DevTools → Network → Slow 3G)
   - [ ] Progress bar animated smoothly even with delayed response
   - [ ] Timestamp updates after API completes

3. **Long-running refresh** (API takes 30+ seconds)
   - [ ] Progress bar keeps animating
   - [ ] Badge doesn't reappear until refresh completes
   - [ ] Timestamp is accurate when refresh finishes

4. **Page loses focus then regains**
   - [ ] Timestamp still accurate after returning
   - [ ] No double-updates or skipped updates

5. **Tab open for 24+ hours**
   - [ ] Color eventually changes to yellow (12h) then red (24h)
   - [ ] No console errors from long-running state

---

## Performance Testing

### Lighthouse Audit
```bash
# In Chrome DevTools:
# Lighthouse → Generate report
```
Expected: No significant regression in performance score

### Bundle Size Impact
```bash
# Compare before/after build sizes
du -sh frontend/build/
```
Expected: < 1 MB increase

### CSS File Size
```bash
# Check CSS changes
wc -c frontend/src/pages/FeedPage.css
```
Expected: +1-2 KB

---

## Browser Testing Matrix

| Browser | Version | Desktop | Mobile | Notes |
|---------|---------|---------|--------|-------|
| Chrome | Latest | ✓ | ✓ | Full support |
| Firefox | Latest | ✓ | ✓ | Full support |
| Safari | Latest | ✓ | ✓ | Full support |
| Edge | Latest | ✓ | ✓ | Full support |
| IE 11 | - | ✗ | - | Not supported (but project may not need it) |

---

## Sign-Off Checklist

- [ ] Visual appearance correct on desktop
- [ ] Visual appearance correct on mobile
- [ ] Hover effects work as expected
- [ ] Tooltip shows on hover
- [ ] Time updates in real-time
- [ ] Color changes at 12h and 24h thresholds
- [ ] Glow animation only shows for fresh data
- [ ] Refresh action updates timestamp correctly
- [ ] No console errors
- [ ] Performance is acceptable
- [ ] Responsive design works at all breakpoints
- [ ] Accessibility features present
- [ ] No UI regressions in other elements

**Ready for production deployment! ✓**
