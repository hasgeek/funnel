const LazyloadImg = {
  init(imgClassName) {
    if (document.querySelector(`.${imgClassName}`)) {
      LazyloadImg.addObserver(imgClassName);
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
          },
        );
        observer.observe(img);
      }
    });
  },
};

export default LazyloadImg;
