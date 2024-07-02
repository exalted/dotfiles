const console = {
  log: finicky.log,  // so that you can `console.log` like you're used to
};

const zoomLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/(.+\.)?zoom\.us(\/[^&]+)/;
const googleVideoCallLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/((chrome|plus|hangouts|meet)\.google\.com\/.+?)&/;
const pivotalTrackerLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/www\.pivotaltracker\.com(\/.+?)&/;

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
    // Extract zoom meeting link when clicked from Mailplane
    {
      match: ({ opener: { bundleId }, urlString }) => {
        if (bundleId !== 'com.mailplaneapp.Mailplane3') {
          return false;
        }

        return zoomLinkFromGCal.test(decodeURIComponent(urlString));
      },
      url: ({ urlString }) => {
        const matches = zoomLinkFromGCal.exec(decodeURIComponent(urlString));
        const pathname = matches[3];

        return `https://zoom.us${pathname}`;
      },
    },
    // Extract video call link for various Google services when clicked from Mailplane
    {
      match: ({ opener: { bundleId }, urlString }) => {
        if (bundleId !== 'com.mailplaneapp.Mailplane3') {
          return false;
        }

        return googleVideoCallLinkFromGCal.test(decodeURIComponent(urlString));
      },
      url: ({ urlString }) => {
        const matches = googleVideoCallLinkFromGCal.exec(decodeURIComponent(urlString));
        const match = matches[2];

        return `https://${match}`;
      },
    },
    // Extract pivotaltracker link when clicked from Mailplane
    {
      match: ({ opener: {  bundleId }, urlString }) => {
        if (bundleId !== 'com.mailplaneapp.Mailplane3') {
          return false;
        }

        return pivotalTrackerLinkFromGCal.test(decodeURIComponent(urlString));
      },
      url: ({ urlString }) => {
        const matches = pivotalTrackerLinkFromGCal.exec(
          decodeURIComponent(urlString)
        );
        const pathname = matches[2];

        return `https://www.pivotaltracker.com${pathname}`;
      },
    },
  ],
  handlers: [
    {
      match: finicky.matchHostnames(['localhost', '127.0.0.1', /\.local$/, /\.convox$/]),
      browser: 'Google Chrome',
    },
    {
      match: finicky.matchHostnames([/(.+\.)?pivotaltracker\.com/]),
      browser: 'Pivotal Tracker',
    },
    {
      match: finicky.matchHostnames([/(chrome|plus|hangouts|meet)\.google\.com/]),
      browser: 'Google Chrome',
    },
    {
      match: finicky.matchHostnames([/(.+\.)?zoom\.us/]),
      browser: 'us.zoom.xos',
    },
  ],
};
