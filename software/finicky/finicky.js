const zoomLinkFromGCal = /https?:\/\/(.+\.)?google\.com\/url\?q=https?:\/\/zoom\.us(\/.+?)&/;

module.exports = {
  options: {
    // Hide the finicky icon from the top bar
    hideIcon: true
  },
  defaultBrowser: 'Safari',
  rewrite: [
    // Redirect all urls to use https
    {
      match: ({ url }) => url.host !== 'localhost',
      url: ({ url }) => ({ ...url, protocol: 'https' })
    },
    // Extract zoom meeting link when clicked from Mailplane
    {
      match: ({ sourceBundleIdentifier, urlString }) => {
        if (sourceBundleIdentifier !== 'com.mailplaneapp.Mailplane3') { return false }

        return zoomLinkFromGCal.test(urlString);
      },
      url: ({ urlString }) => {
        const matches = urlString.match(zoomLinkFromGCal);

        return {
          protocol: 'https',
          host: 'zoom.us',
          pathname: matches[2]
        };
      }
    }
  ],
  handlers: [
    {
      match: finicky.matchDomains([ 'localhost' ]),
      browser: 'Google Chrome'
    },
    {
      match: finicky.matchDomains([ /(.+\.)?pivotaltracker\.com/ ]),
      browser: 'Pivotal Tracker'
    },
    {
      match: finicky.matchDomains([ /(plus|hangouts|meet)\.google\.com/ ]),
      browser: 'Google Chrome'
    },
    {
      match: finicky.matchDomains([ /(.+\.)?zoom\.us/ ]),
      browser: 'us.zoom.xos'
    }
  ]
};
