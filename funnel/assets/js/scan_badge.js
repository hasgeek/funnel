import Ractive from "ractive";
import jsQR from "jsqr";

const badgeScan = {
  init({checkinApiUrl, wrapperId, templateId, projectTitle, eventTitle}) {
    
    let badgeScanComponent = new Ractive({
      el: `#${wrapperId}`,
      template: `#${templateId}`,
      data: {
        projectTitle: projectTitle,
        eventTitle: eventTitle,
        video: {},
        error: 'Unable to access video. Please make sure you have a camera enabled',
        attendeeName: '',
        attendeeFound: false,
        scanning: true,
        showModal: false,
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

        let url = checkinApiUrl.replace('puk', qrcode.substring(0,8));
        let csrfToken = $("meta[name='csrf-token']").attr('content');
        let formValues = `checkin=t&csrf_token=${csrfToken}`;

        $.ajax({
          type: 'POST',
          url:  url,
          data : formValues,
          timeout: 5000,
          dataType: 'json',
          success(response) {
            badgeScanComponent.set({
              'scanning': false,
              'attendeeFound': true,
              'attendeeName': response.attendee.fullname
            });
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
      setupVideo: function(event) {
        if (event)  {
          event.original.preventDefault();
        }
        let video = document.createElement("video");

        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }).then((stream) => {
          this.set('video', video);
          this.get('video').srcObject = stream;
          this.get('video').setAttribute("playsinline", true);
          this.get('video').play();

          window.requestAnimationFrame(badgeScanComponent.renderFrame);
        });
      },
      oncomplete: function() {
        this.setupVideo('');
      }
    });
  },
};

$(() => {
  window.HasGeek.BadgeScanInit = function (eventConfig) {
    badgeScan.init(eventConfig);
  }
});
