// menu
const button = document.querySelector('#menubtn');
const list = document.getElementById('navbar');


button.addEventListener('click', function() {
  if (list.classList.contains('hidden')) {
    list.classList.remove('hidden');
    
  } else {
    list.classList.add('hidden');
  }
})