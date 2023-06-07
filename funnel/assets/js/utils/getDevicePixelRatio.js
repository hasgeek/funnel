/*! GetDevicePixelRatio | Author: Tyson Matanich, 2012 | License: MIT */
(function setGlobalFn(n) {
  /* eslint-disable no-return-assign */
  n.getDevicePixelRatio = function getRatio() {
    let t = 1;
    return (
      n.screen.systemXDPI !== undefined &&
      n.screen.logicalXDPI !== undefined &&
      n.screen.systemXDPI > n.screen.logicalXDPI
        ? (t = n.screen.systemXDPI / n.screen.logicalXDPI)
        : n.devicePixelRatio !== undefined && (t = n.devicePixelRatio),
      t
    );
  };
})(window);
