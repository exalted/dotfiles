const console = {
  log: finicky.log,  // so that you can `console.log` like you're used to
};

// const zoomLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/(.+\.)?zoom\.us(\/[^&]+)/;
// const googleVideoCallLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/((chrome|plus|hangouts|meet)\.google\.com\/.+?)&/;

module.exports = {
  options: {
    // Hide the finicky icon from the top bar
    hideIcon: true,
  },
  defaultBrowser: 'Safari',
  rewrite: [
    // Redirect all urls to use https
    {
      match: ({ url }) => (
        url.protocol === 'http' &&
        url.host !== 'localhost' &&
        url.host !== '127.0.0.1'
      ),
      url: ({ url }) => ({ ...url, protocol: 'https' }),
    },
    // // Extract zoom meeting link when clicked from Mailplane
    // {
    //   match: ({ opener: { bundleId }, urlString }) => {
    //     if (bundleId !== 'com.mailplaneapp.Mailplane3') {
    //       return false;
    //     }

    //     return zoomLinkFromGCal.test(decodeURIComponent(urlString));
    //   },
    //   url: ({ urlString }) => {
    //     const matches = zoomLinkFromGCal.exec(decodeURIComponent(urlString));
    //     const pathname = matches[3];

    //     return `https://zoom.us${pathname}`;
    //   },
    // },
    // Extract video call link for various Google services when clicked from Mailplane
    // {
    //   match: ({ opener: { bundleId }, urlString }) => {
    //     if (bundleId !== 'com.mailplaneapp.Mailplane3') {
    //       return false;
    //     }

    //     return googleVideoCallLinkFromGCal.test(decodeURIComponent(urlString));
    //   },
    //   url: ({ urlString }) => {
    //     const matches = googleVideoCallLinkFromGCal.exec(decodeURIComponent(urlString));
    //     const match = matches[2];

    //     return `https://${match}`;
    //   },
    // },
  ],
  handlers: [
    {
      match: finicky.matchHostnames(['localhost', '127.0.0.1', /\.local$/, /\.convox$/]),
      browser: {
        name: 'Google Chrome',
        profile: "Default",
      },
    },
    {
      match: finicky.matchHostnames([/(chrome|plus|hangouts|meet)\.google\.com/]),
      browser: {
        name: 'Google Chrome',
        profile: "Default",
      },
    },
    {
      match: finicky.matchHostnames([/(.+\.)?zoom\.us/]),
      browser: 'us.zoom.xos',
    },
    // {
    //   match: ({ urlString }) => {
    //     return /https:\/\/balsamiq\.atlassian\.net\/(jira|browse\/[A-Z]+-[0-9]+)/.test(urlString);
    //   },
    //   browser: 'Balsamiq Jira',
    // },
  ],
};
