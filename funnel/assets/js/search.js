import Ractive from "ractive";

const Search = {
  init({}) {
  }
};

$(() => {
  window.HasGeek.Search = function (config) {
    Search.init(config);
  }
});
