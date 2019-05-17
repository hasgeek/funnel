import Ractive from "ractive";
import jsQR from "jsqr";

const badgeScan = {
  init({participantApiUrl, wrapperId, templateId, projectTitle}) {
    
    let badgeScanComponent = new Ractive({
      el: `#${wrapperId}`,
      template: `#${templateId}`,
      data: {
        projectTitle: projectTitle,
        video: {},
        error: 'Unable to access video. Please make sure you have a camera enabled',
        attendeeName: '',
        attendeeFound: false,
        scanning: true,
        showModal: false,
        contacts: []
      },
      closeModal(event) {
        event.original.preventDefault();
        $.modal.close();
        this.set('showModal', false);
      },
      checkinAttendee(qrcode) {
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
          url:  participantApiUrl,
          data : formValues,
          timeout: 5000,
          dataType: 'json',
          success(response) {
            console.log('response', response);
            badgeScanComponent.set({
              'scanning': false,
              'attendeeFound': true,
              'participant': response.participant,
            });
            badgeScanComponent.push('contacts', response.participant);
          },
          error() {
            badgeScanComponent.set({
              'scanning': false,
              'attendeeFound': false
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
            this.checkinAttendee(qrcode.data);
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
  window.HasGeek.BadgeScanInit = function (eventConfig) {
    badgeScan.init(eventConfig);
  }
});
