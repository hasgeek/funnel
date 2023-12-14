const Video = {
  /* Takes argument
     `videoWrapper`: video container element,
     'videoUrl': video url
    Video id is extracted from the video url (getVideoTypeAndId).
    The videoID is then used to generate the iframe html.
    The generated iframe is added to the video container element.
  */
  validHostnames: [
    'www.youtube.com',
    'youtube.com',
    'youtu.be',
    'y2u.be',
    'www.vimeo.com',
    'vimeo.com',
    'player.vimeo.com',
  ],
  getVideoTypeAndId(videoUrl) {
    let videoId;
    let paramId;
    let type;
    const url = new URL(videoUrl);
    const { hostname } = url;
    let regexMatch;
    if (this.validHostnames.includes(hostname)) {
      if (hostname.includes('vimeo')) {
        type = 'vimeo';
        paramId = url.searchParams.get('h');
        if (paramId) {
          regexMatch = url.pathname.match(/\/(video\/)?(?<videoId>[A-Za-z0-9._%-]*)/);
          videoId = regexMatch.groups.videoId;
        } else {
          regexMatch = url.pathname.match(
            /\/(video\/)?(?<videoId>[A-Za-z0-9._%-]*)?(\/)?(?<paramId>[A-Za-z0-9._%-]*)/
          );
          videoId = regexMatch.groups.videoId;
          paramId = regexMatch.groups.paramId;
        }
      } else {
        type = 'youtube';
        videoId = url.searchParams.get('v');
        if (!videoId) {
          regexMatch = url.pathname.match(
            /\/(embed\/|live\/)?(?<videoId>[A-Za-z0-9._%-]*)/
          );
          videoId = regexMatch.groups.videoId;
        }
      }
      return {
        type,
        videoId,
        paramId,
      };
    }
    return {};
  },
  embedIframe(videoWrapper, videoUrl) {
    let videoEmbedUrl = '';
    const { type, videoId, paramId } = this.getVideoTypeAndId(videoUrl);
    if (type === 'youtube') {
      videoEmbedUrl = `<iframe src='//www.youtube.com/embed/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    } else if (type === 'vimeo') {
      videoEmbedUrl = `<iframe src='https://player.vimeo.com/video/${videoId}${
        paramId ? `?h=${paramId}` : ''
      }' frameborder='0' allowfullscreen></iframe>`;
    }
    if (videoEmbedUrl) {
      videoWrapper.innerHTML = videoEmbedUrl;
    }
  },
};

export default Video;
