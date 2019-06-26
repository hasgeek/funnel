import vCardsJS from "vcards-js";

$(() => {
  window.HasGeek.downloadVcard = function (element, fullname, email, phone, company) {
    let vCard = vCardsJS();
    let lastName;
    [vCard.firstName, ...lastName] = fullname.split(' ');
    vCard.lastName = lastName.join(' ');
    vCard.email = email;
    vCard.cellPhone = phone;    
    vCard.organization = company;
    element.setAttribute('href', 'data:text/x-vcard;charset=utf-8,' + encodeURIComponent(vCard.getFormattedString()));
    element.setAttribute('download', `${vCard.firstName}.vcf`);
  };
});
