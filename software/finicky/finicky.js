const console = finicky;  // so that you can `console.log` like you're used to

const zoomLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/(.+\.)?zoom\.us(\/[^&]+)/;
const pivotalTrackerLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/www\.pivotaltracker\.com(\/.+?)&/;

module.exports = {
  options: {
    // Hide the finicky icon from the top bar
    hideIcon: true
  },
  defaultBrowser: 'Safari',
  rewrite: [
    // Redirect all urls to use https
    {
      match: ({ url }) => url.protocol === 'http' && url.host !== 'localhost',
      url: ({ url }) => ({ ...url, protocol: 'https' })
    },
    // Extract zoom meeting link when clicked from Mailplane
    {
      match: ({ sourceBundleIdentifier, urlString }) => {
        if (sourceBundleIdentifier !== 'com.mailplaneapp.Mailplane3') { return false }

        return zoomLinkFromGCal.test(decodeURIComponent(urlString));
      },
      url: ({ urlString }) => {
        const matches = zoomLinkFromGCal.exec(decodeURIComponent(urlString));

        return {
          protocol: 'https',
          host: 'zoom.us',
          pathname: matches[3]
        };
      }
    },
    // Extract pivotaltracker link when clicked from Mailplane
    {
      match: ({ sourceBundleIdentifier, urlString }) => {
        if (sourceBundleIdentifier !== 'com.mailplaneapp.Mailplane3') { return false }

        return pivotalTrackerLinkFromGCal.test(decodeURIComponent(urlString));
      },
      url: ({ urlString }) => {
        const matches = pivotalTrackerLinkFromGCal.exec(decodeURIComponent(urlString));

        return {
          protocol: 'https',
          host: 'www.pivotaltracker.com',
          pathname: matches[2]
        };
      }
    }
  ],
  handlers: [
    {
      match: finicky.matchDomains([ 'localhost', /\.local$/, /\.convox$/ ]),
      browser: 'Google Chrome'
    },
    {
      match: finicky.matchDomains([ /(.+\.)?pivotaltracker\.com/ ]),
      browser: 'Pivotal Tracker'
    },
    {
      match: finicky.matchDomains([ /(chrome|plus|hangouts|meet)\.google\.com/ ]),
      browser: 'Google Chrome'
    },
    {
      match: finicky.matchDomains([ /(.+\.)?zoom\.us/ ]),
      browser: 'us.zoom.xos'
    }
  ]
};
