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
        canvas: '',
        canvasElement: '',
        error: 'Unable to access video. Please make sure you have a camera enabled',
        attendeeName: '',
        attendeeFound: false,
        scanning: true,
        showModal: false,
        timerId: '',
        facingMode: true,
        cameras: [],
        selectedCamera: '',
      },
      closeModal(event) {
        if (event) event.original.preventDefault();
        $.modal.close();
        this.set('showModal', false);
        this.startRenderFrameLoop();
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
          timeout: window.HasGeek.config.ajaxTimeout,
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
          },
          complete() {
            window.setTimeout(function() {
              badgeScanComponent.closeModal();
            }, window.HasGeek.config.closeModalTimeout);
          }
        });
      },
      startRenderFrameLoop(event) {
        if(event) event.original.preventDefault();
        let timerId;
        timerId = window.requestAnimationFrame(this.renderFrame);
        this.set('timerId', timerId);
      },
      stopRenderFrameLoop(event) {
        if(event) event.original.preventDefault();
        let timerId = this.get('timerId');
        if(timerId) window.cancelAnimationFrame(timerId);
        this.set('timerId', '');
      },
      verifyQRDecode(qrcode) {
        if (qrcode && qrcode.data.length === 16 && !this.get('showModal')) {
          this.stopRenderFrameLoop();
          this.checkinAttendee(qrcode.data);
        } else {
          this.startRenderFrameLoop();
        }
      },
      renderFrame() {
        let canvasElement = this.get('canvasElement');
        let canvas = this.get('canvas');
        let video = this.get('video');

        if (video.readyState === video.HAVE_ENOUGH_DATA) {
          canvasElement.height = video.videoHeight;
          canvasElement.width = video.videoWidth;
          canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
          let imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
          let qrcode = jsQR(imageData.data, imageData.width, imageData.height);
          this.verifyQRDecode(qrcode);
        } else {
          this.startRenderFrameLoop();
        }
      },
      stopVideo() {
        let stream = this.get('video').srcObject;
        if (typeof stream !== 'undefined') {
          stream.getTracks().forEach(track => {
            track.stop();
          });
        }
      },
      setupVideo() {
        let video = document.getElementById('qrreader');
        let canvasElement = document.createElement('canvas');
        let canvas = canvasElement.getContext("2d");
        let videoConstraints = {};
        if (this.get('selectedCamera') === '') {
          videoConstraints.facingMode = 'environment';
        } else {
          videoConstraints.deviceId = { exact: this.get('selectedCamera') };
        }
        let constraints = { video: videoConstraints, audio: false };

        navigator.mediaDevices.getUserMedia(constraints).then((stream) => {
          this.set('video', video);
          this.get('video').srcObject = stream;
          this.get('video').play();
          this.set('canvasElement', canvasElement);
          this.set('canvas', canvas);
          this.startRenderFrameLoop();
          if(this.get('cameras').length === 0) navigator.mediaDevices.enumerateDevices().then(badgeScanComponent.getDeviceCameras);
        });
      },
      switchCamera(event) {
        event.original.preventDefault();
        this.stopRenderFrameLoop();
        this.stopVideo();
        this.setupVideo();
      },
      getDeviceCameras(mediaDevices) {
        let count = 0;
        mediaDevices.forEach(mediaDevice => {
          if (mediaDevice.kind === 'videoinput') {
            badgeScanComponent.push('cameras', {'value': mediaDevice.deviceId, 'label': mediaDevice.label || `Camera ${count+1}`});
          }
        });
      },
      oncomplete() {
        this.setupVideo();
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
