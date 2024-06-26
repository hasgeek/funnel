import 'select2';

const EnableAutocompleteWidgets = {
  lastuserAutocomplete(options) {
    const assembleUsers = function getUsersMap(users) {
      return users.map((user) => {
        return { id: user.buid, text: user.label };
      });
    };

    $(`#${options.id}`).select2({
      placeholder: 'Search for a user',
      multiple: options.multiple,
      minimumInputLength: 2,
      ajax: {
        url: options.autocompleteEndpoint,
        dataType: 'jsonp',
        data(params) {
          if ('clientId' in options) {
            return {
              q: params.term,
              client_id: options.clientId,
              session: options.sessionId,
            };
          }
          return {
            q: params.term,
          };
        },
        processResults(data) {
          let users = [];
          if (data.status === 'ok') {
            users = assembleUsers(data.users);
          }
          return { more: false, results: users };
        },
      },
    });
  },
  textAutocomplete(options) {
    $(`#${options.id}`).select2({
      placeholder: 'Type to select',
      multiple: options.multiple,
      minimumInputLength: 2,
      ajax: {
        url: options.autocompleteEndpoint,
        dataType: 'json',
        data(params, page) {
          return {
            q: params.term,
            page,
          };
        },
        processResults(data) {
          return {
            more: false,
            results: data[options.key].map((item) => {
              return { id: item, text: item };
            }),
          };
        },
      },
    });
  },
  geonameAutocomplete(options) {
    $(options.selector).select2({
      placeholder: 'Search for a location',
      multiple: true,
      minimumInputLength: 2,
      ajax: {
        url: options.autocompleteEndpoint,
        dataType: 'jsonp',
        data(params) {
          return {
            q: params.term,
          };
        },
        processResults(data) {
          const rdata = [];
          if (data.status === 'ok') {
            for (const r of data.result) {
              rdata.push({
                id: r.geonameid,
                text: r.picker_title,
              });
            }
          }
          return { more: false, results: rdata };
        },
      },
    });

    // Setting label for Geoname ids
    let val = $(options.selector).val();
    if (val) {
      val = val.map((id) => {
        return `name=${id}`;
      });
      const qs = val.join('&');
      $.ajax(`${options.getnameEndpoint}?${qs}`, {
        accepts: 'application/json',
        dataType: 'jsonp',
      }).done((data) => {
        $(options.selector).empty();
        const rdata = [];
        if (data.status === 'ok') {
          for (const r of data.result) {
            $(options.selector).append(
              `<option value="${r.geonameid}" selected>${r.picker_title}</option>`,
            );
            rdata.push(r.geonameid);
          }
          $(options.selector).val(rdata).trigger('change');
        }
      });
    }
  },
};

export default EnableAutocompleteWidgets;
