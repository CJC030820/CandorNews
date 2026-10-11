/**
 * PageTransition Debug Helper
 * Add this to your browser console to verify animations are working
 */

window.debugPageTransition = function() {
  console.log('=== Page Transition Debug ===');
  
  // 1. Check if PageTransition component exists
  const pageTransition = document.querySelector('.page-transition');
  if (!pageTransition) {
    console.error('❌ .page-transition element not found in DOM');
    return;
  }
  console.log('✅ .page-transition element found');
  console.log('Current classes:', pageTransition.className);
  
  // 2. Check computed styles
  const styles = window.getComputedStyle(pageTransition);
  console.log('Computed opacity:', styles.opacity);
  console.log('Computed animation:', styles.animation);
  
  // 3. Check if CSS is loaded
  const sheets = document.styleSheets;
  let foundPageTransitionCSS = false;
  for (let sheet of sheets) {
    try {
      const rules = sheet.cssRules || sheet.rules;
      for (let rule of rules) {
        if (rule.selectorText && rule.selectorText.includes('page-transition')) {
          foundPageTransitionCSS = true;
          console.log('✅ Found CSS rule:', rule.selectorText);
        }
        if (rule.name && (rule.name === 'fadeIn' || rule.name === 'fadeOut')) {
          console.log('✅ Found animation:', rule.name);
        }
      }
    } catch (e) {
      // Cross-origin stylesheets will throw
    }
  }
  
  if (!foundPageTransitionCSS) {
    console.warn('⚠️  No page-transition CSS rules found');
  }
  
  // 4. Test animation by simulating route change
  console.log('\n=== Testing Animation ===');
  console.log('Changing class to "hidden"...');
  pageTransition.classList.remove('visible');
  pageTransition.classList.add('hidden');
  
  setTimeout(() => {
    console.log('Changing class back to "visible"...');
    pageTransition.classList.remove('hidden');
    pageTransition.classList.add('visible');
    console.log('Animation test complete. You should have seen a fade out/in.');
  }, 500);
};

console.log('Page Transition Debug Helper loaded. Run: window.debugPageTransition()');
