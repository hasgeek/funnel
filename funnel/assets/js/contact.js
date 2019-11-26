import vCardsJS from 'vcards-js';

$(() => {
  window.HasGeek.downloadVcard = function(
    element,
    fullname,
    email,
    phone,
    company
  ) {
    const vCard = vCardsJS();
    vCard.firstName = fullname;
    vCard.email = email;
    vCard.cellPhone = phone;
    vCard.organization = company;
    element.setAttribute(
      'href',
      `data:text/x-vcard;charset=utf-8,${encodeURIComponent(
        vCard.getFormattedString()
      )}`
    );
    element.setAttribute('download', `${vCard.firstName}.vcf`);
  };
});
