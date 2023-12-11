const LazyloadImg = {
  init(imgClassName) {
    const intersectionObserverComponents =
      function intersectionObserverComponents() {
        LazyloadImg.addObserver(imgClassName);
      };

    if (document.querySelector(`.${imgClassName}`)) {
      if (
        !(
          'IntersectionObserver' in global &&
          'IntersectionObserverEntry' in global &&
          'intersectionRatio' in IntersectionObserverEntry.prototype
        )
      ) {
        const polyfill = document.createElement('script');
        polyfill.setAttribute('type', 'text/javascript');
        polyfill.setAttribute(
          'src',
          'https://cdn.polyfill.io/v2/polyfill.min.js?features=IntersectionObserver'
        );
        polyfill.onload = function loadintersectionObserverComponents() {
          intersectionObserverComponents();
        };
        document.head.appendChild(polyfill);
      } else {
        intersectionObserverComponents();
      }
    }
  },
  displayImages(img) {
    img.target.src = img.target.dataset.src;
  },
  addObserver(imgClassName) {
    this.imgItems = [...document.querySelectorAll(`.${imgClassName}`)];
    this.imgItems.forEach((img) => {
      if (img) {
        let observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                LazyloadImg.displayImages(entry);
                observer = observer.disconnect();
              }
            });
          },
          {
            rootMargin: '0px',
            threshold: 0,
          }
        );
        observer.observe(img);
      }
    });
  },
};

export default LazyloadImg;
