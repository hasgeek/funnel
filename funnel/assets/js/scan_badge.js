import jsQR from 'jsqr';
import { RactiveApp } from './utils/ractive_util';

const badgeScan = {
  init({ checkinApiUrl, wrapperId, templateId, projectTitle, ticketEventTitle }) {
    const badgeScanComponent = new RactiveApp({
      el: `#${wrapperId}`,
      template: `#${templateId}`,
      data: {
        projectTitle,
        ticketEventTitle,
        video: {},
        canvas: '',
        canvasElement: '',
        error: '',
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
      async checkinAttendee(qrcode) {
        this.set({
          scanning: true,
          showModal: true,
        });
        $('#status-msg').modal('show');
        const url = `${checkinApiUrl.replace('puk', qrcode.substring(0, 8))}?t`;
        const csrfToken = $("meta[name='csrf-token']").attr('content');

        const closeModal = () => {
          window.setTimeout(() => {
            badgeScanComponent.closeModal();
          }, window.Hasgeek.Config.closeModalTimeout);
        };

        const handleError = () => {
          badgeScanComponent.set({
            scanning: false,
            attendeeFound: false,
          });
          closeModal();
        };

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            csrf_token: csrfToken,
          }).toString(),
        }).catch(window.toastr.error(window.Hasgeek.Config.errorMsg.networkError));
        if (response && response.ok) {
          const responseData = await response.json();
          if (responseData) {
            badgeScanComponent.set({
              scanning: false,
              attendeeFound: true,
              attendeeName: responseData.attendee.fullname,
            });
            closeModal();
          } else {
            handleError();
          }
        } else {
          handleError();
        }
      },
      startRenderFrameLoop(event) {
        if (event) event.original.preventDefault();
        const timerId = window.requestAnimationFrame(this.renderFrame);
        this.set('timerId', timerId);
      },
      stopRenderFrameLoop(event) {
        if (event) event.original.preventDefault();
        const timerId = this.get('timerId');
        if (timerId) window.cancelAnimationFrame(timerId);
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
      stopVideo() {
        const stream = this.get('video').srcObject;

        if (typeof stream !== 'undefined') {
          stream.getTracks().forEach((track) => {
            track.stop();
          });
        }
      },
      setupVideo() {
        const video = document.getElementById('qrreader');
        const canvasElement = document.createElement('canvas');
        const canvas = canvasElement.getContext('2d');
        const videoConstraints = {};

        if (this.get('selectedCamera') === '') {
          videoConstraints.facingMode = 'environment';
        } else {
          videoConstraints.deviceId = {
            exact: this.get('selectedCamera'),
          };
        }

        const constraints = {
          video: videoConstraints,
          audio: false,
        };
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          navigator.mediaDevices.getUserMedia(constraints).then((stream) => {
            this.set('video', video);
            this.get('video').srcObject = stream;
            this.get('video').play();
            this.set('canvasElement', canvasElement);
            this.set('canvas', canvas);
            this.startRenderFrameLoop();
            if (this.get('cameras').length === 0)
              navigator.mediaDevices
                .enumerateDevices()
                .then(badgeScanComponent.getDeviceCameras);
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
      switchCamera(event) {
        event.original.preventDefault();
        this.stopRenderFrameLoop();
        this.stopVideo();
        this.setupVideo();
      },
      getDeviceCameras(mediaDevices) {
        const count = 0;
        mediaDevices.forEach((mediaDevice) => {
          if (mediaDevice.kind === 'videoinput') {
            badgeScanComponent.push('cameras', {
              value: mediaDevice.deviceId,
              label: mediaDevice.label || `Camera ${count + 1}`,
            });
          }
        });
      },
      oncomplete() {
        this.setupVideo();
        this.renderFrame = this.renderFrame.bind(this);
      },
    });
  },
};
$(() => {
  window.Hasgeek.badgeScanInit = function badgeScanInit(ticketEventConfig) {
    badgeScan.init(ticketEventConfig);
  };
});
