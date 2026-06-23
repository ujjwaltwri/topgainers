with open('frontend/js/app.js', 'r') as f:
    js = f.read()

js_addition = '''
  // Mobile Sidebar Drawer Logic
  const mobileFilterBtn = document.getElementById('mobile-filter-btn');
  const closeSidebarBtn = document.getElementById('close-sidebar');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  if (mobileFilterBtn && sidebar && sidebarOverlay) {
    mobileFilterBtn.addEventListener('click', () => {
      sidebar.classList.add('open');
      sidebarOverlay.classList.remove('hidden');
    });

    const closeSidebar = () => {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.add('hidden');
    };

    if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);
  }
'''

# insert before the end of the DOMContentLoaded block
js = js.replace('}); // end DOMContentLoaded', js_addition + '\n}); // end DOMContentLoaded')

with open('frontend/js/app.js', 'w') as f:
    f.write(js)

print("JS updated.")
