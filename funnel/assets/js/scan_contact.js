import Ractive from "ractive";
import jsQR from "jsqr";
import vCardsJS from "vcards-js";

const badgeScan = {
  init({getContactApiUrl, wrapperId, templateId}) {
    
    let badgeScanComponent = new Ractive({
      el: `#${wrapperId}`,
      template: `#${templateId}`,
      data: {
        video: {},
        error: 'Unable to access video. Please make sure you have a camera enabled',
        contact: '',
        contactFound: false,
        scanning: true,
        showModal: false,
        errorMsg: '',
        contacts: []
      },
      closeModal(event) {
        event.original.preventDefault();
        $.modal.close();
        this.set('showModal', false);
      },
      downloadContact(event) {
        let contact = badgeScanComponent.get(event.keypath);
        let vCard = vCardsJS();
        let lastName;
        [vCard.firstName, ...lastName] = contact.fullname.split(' ');
        vCard.lastName = lastName.join(' ');
        vCard.email = contact.email;
        vCard.cellPhone = contact.phone;    
        vCard.organization = contact.company;
        event.node.setAttribute('href', 'data:text/x-vcard;charset=utf-8,' + encodeURIComponent(vCard.getFormattedString()));
        event.node.setAttribute('download', `${vCard.firstName}.vcf`);
      },
      getContact(qrcode) {
        this.set({
          'scanning': true,
          'showModal': true
        });

        $("#status-msg").modal('show');

        let puk = qrcode.substring(0,8);
        let key =  qrcode.substring(8);
        let formValues = `puk=${puk}&key=${key}`;

        $.ajax({
          type: 'POST',
          url:  getContactApiUrl,
          data : formValues,
          timeout: 5000,
          dataType: 'json',
          success(response) {
            badgeScanComponent.set({
              'scanning': false,
              'contactFound': true,
              'contact': response.contact,
            });
            if(!badgeScanComponent.get('contacts').some(contact => 
              contact.fullname === response.contact.fullname && 
              contact.email === response.contact.email)) {
              badgeScanComponent.push('contacts', response.contact);
            }
          },
          error(response) {
            let errorMsg;
            if (response.readyState === 4) {
              if (response.status === 500) {
                errorMsg ='Internal Server Error. Please reload and try again.';
              } else {
                errorMsg = JSON.parse(response.responseText).message;
              }
            } else {
              errorMsg = 'Unable to connect. Please reload and try again.';
            }
            badgeScanComponent.set({
              'scanning': false,
              'contactFound': false,
              'errorMsg': errorMsg
            });
          }
        });
      },
      renderFrame() {
        let canvasElement = document.getElementById("qrreader-canvas");
        let canvas = canvasElement.getContext("2d");

        if (this.get('video').readyState === this.get('video').HAVE_ENOUGH_DATA) {
          canvasElement.height = this.get('video').videoHeight;
          canvasElement.width = this.get('video').videoWidth;
          canvas.drawImage(this.get('video'), 0, 0, canvasElement.width, canvasElement.height);
          let imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
          let qrcode = jsQR(imageData.data, imageData.width, imageData.height);

          if (qrcode && qrcode.data.length === 16 && !this.get('showModal')) {
            this.getContact(qrcode.data);
          }
        }
        window.requestAnimationFrame(badgeScanComponent.renderFrame);
      },
      setupVideo(event) {
        if (event)  {
          event.original.preventDefault();
        }
        let video = document.createElement("video");

        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }).then((stream) => {
          this.set('video', video);
          this.get('video').srcObject = stream;
          this.get('video').setAttribute("playsinline", true);
          this.get('video').play();

          window.requestAnimationFrame(this.renderFrame);
        });
      },
      oncomplete() {
        this.setupVideo('');
        this.renderFrame = this.renderFrame.bind(this);
      }
    });
  },
};

$(() => {
  window.HasGeek.BadgeScanInit = function (scanConfig) {
    badgeScan.init(scanConfig);
  }
});
