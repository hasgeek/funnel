import jsQR from 'jsqr';
import vCardsJS from 'vcards-js';
import toastr from 'toastr';
import Form from './utils/formhelper';
import { RactiveApp } from './utils/ractive_util';

const badgeScan = {
  init({ getContactApiUrl, wrapperId, templateId }) {
    const badgeScanComponent = new RactiveApp({
      el: `#${wrapperId}`,
      template: `#${templateId}`,
      data: {
        video: {},
        error: '',
        contact: '',
        contactFound: false,
        scanning: true,
        showModal: false,
        errorMsg: '',
        contacts: [],
      },
      closeModal(event) {
        event.original.preventDefault();
        $.modal.close();
        this.set('showModal', false);
        this.startRenderFrameLoop();
      },
      downloadContact(event) {
        const contact = badgeScanComponent.get(event.keypath);
        const vCard = vCardsJS();
        let lastName;
        [vCard.firstName, ...lastName] = contact.fullname.split(' ');
        vCard.lastName = lastName.join(' ');
        vCard.email = contact.email;
        vCard.cellPhone = contact.phone;
        vCard.organization = contact.company;
        event.node.setAttribute(
          'href',
          `data:text/x-vcard;charset=utf-8,${encodeURIComponent(
            vCard.getFormattedString()
          )}`
        );
        event.node.setAttribute('download', `${vCard.firstName}.vcf`);
      },
      async getContact(qrcode) {
        this.set({
          scanning: true,
          showModal: true,
        });
        $('#status-msg').modal('show');
        const puk = qrcode.substring(0, 8);
        const key = qrcode.substring(8);
        const formValues = `puk=${encodeURIComponent(puk)}&key=${encodeURIComponent(
          key
        )}`;

        function handleError(error) {
          const errorMsg = Form.getFetchError(error);
          badgeScanComponent.set({
            scanning: false,
            contactFound: false,
            errorMsg,
          });
        }

        const response = await fetch(getContactApiUrl, {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formValues,
        }).catch(() => {
          toastr.error(window.Hasgeek.Config.errorMsg.networkError);
        });
        if (response && response.ok) {
          const responseData = await response.json();
          if (responseData) {
            badgeScanComponent.set({
              scanning: false,
              contactFound: true,
              contact: responseData.contact,
            });

            if (
              !badgeScanComponent
                .get('contacts')
                .some(
                  (contact) =>
                    contact.fullname === responseData.contact.fullname &&
                    contact.email === responseData.contact.email
                )
            ) {
              badgeScanComponent.push('contacts', responseData.contact);
            }
          } else {
            handleError();
          }
        } else {
          handleError();
        }
      },
      startRenderFrameLoop() {
        const timerId = window.requestAnimationFrame(badgeScanComponent.renderFrame);
        this.set('timerId', timerId);
      },
      stopRenderFrameLoop() {
        window.cancelAnimationFrame(badgeScanComponent.get('timerId'));
        this.set('timerId', '');
      },
      verifyQRDecode(qrcode) {
        if (qrcode && qrcode.data.length === 16 && !this.get('showModal')) {
          this.stopRenderFrameLoop();
          this.getContact(qrcode.data);
        } else {
          this.startRenderFrameLoop();
        }
      },
      renderFrame() {
        const canvasElement = this.get('canvasElement');
        const canvas = this.get('canvas');
        const video = this.get('video');

        if (video.readyState === video.HAVE_ENOUGH_DATA) {
          canvasElement.height = video.videoHeight;
          canvasElement.width = video.videoWidth;
          canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
          const imageData = canvas.getImageData(
            0,
            0,
            canvasElement.width,
            canvasElement.height
          );
          const qrcode = jsQR(imageData.data, imageData.width, imageData.height);
          this.verifyQRDecode(qrcode);
        } else {
          this.startRenderFrameLoop();
        }
      },
      setupVideo(event) {
        if (event) {
          event.original.preventDefault();
        }

        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          const video = document.getElementById('qrreader');
          const canvasElement = document.createElement('canvas');
          const canvas = canvasElement.getContext('2d');

          navigator.mediaDevices
            .getUserMedia({ video: { facingMode: 'environment' } })
            .then((stream) => {
              this.set('video', video);
              this.get('video').srcObject = stream;
              this.get('video').setAttribute('playsinline', true);
              this.get('video').play();
              this.set('canvasElement', canvasElement);
              this.set('canvas', canvas);
              this.startRenderFrameLoop();
            });
        } else {
          this.set(
            'error',
            window.gettext(
              'Unable to access video stream. Please make sure you have camera enabled or try a different browser'
            )
          );
        }
      },
      oncomplete() {
        this.setupVideo('');
        this.renderFrame = this.renderFrame.bind(this);
      },
    });
  },
};
$(() => {
  window.Hasgeek.badgeScanInit = function badgeScanInit(scanConfig) {
    badgeScan.init(scanConfig);
  };
});
