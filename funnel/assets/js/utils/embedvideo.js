const Video = {
  /* Takes argument
     `videoWrapper`: video container element,
     'videoUrl': video url
    Video id is extracted from the video url (getVideoTypeAndId).
    The videoID is then used to generate the iframe html.
    The generated iframe is added to the video container element.
  */
  getVideoTypeAndId(url) {
    const regexMatch = url.match(
      /(http:|https:|)\/\/(player.|www.)?(?<service>y2u\.be|vimeo\.com|youtu(be\.com|\.be|be\.googleapis\.com))\/(video\/|embed\/|live\/|watch\?v=|v\/)?(?<videoId>[A-Za-z0-9._%-]*)(&\S+)?(\?h=(?<paramId>[^&]+))?/
    );
    let type = '';
    if (regexMatch && regexMatch.length > 5) {
      if (
        regexMatch.groups.service.indexOf('youtu') > -1 ||
        regexMatch.groups.service.indexOf('y2u') > -1
      ) {
        type = 'youtube';
      } else if (regexMatch.groups.service.indexOf('vimeo') > -1) {
        type = 'vimeo';
        return {
          type,
          videoId: regexMatch.groups.videoId,
          paramId: regexMatch.groups.paramId,
        };
      }
      return {
        type,
        videoId: regexMatch[6],
      };
    }
    return {
      type,
      videoId: url,
    };
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
