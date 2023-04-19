import {
  activateFormWidgets,
  EnableAutocompleteWidgets,
  MapMarker,
} from './utils/formWidgets';
import Form from './utils/formhelper';

$(() => {
  activateFormWidgets();
  window.Hasgeek.Form = {
    textAutocomplete: EnableAutocompleteWidgets.textAutocomplete.bind(Form),
    lastuserAutocomplete: EnableAutocompleteWidgets.lastuserAutocomplete.bind(Form),
    geonameAutocomplete: EnableAutocompleteWidgets.geonameAutocomplete.bind(Form),
    MapMarker,
  };
});
