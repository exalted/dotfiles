module.exports = {
  defaultBrowser: 'Safari',
  handlers: [
    {
      match: finicky.matchDomains([ /(.+\.)?pivotaltracker\.com/ ]),
      browser: 'Pivotal Tracker'
    },
    {
      match: finicky.matchDomains([ /(plus|hangouts)\.google\.com/ ]),
      browser: 'Google Chrome'
    }
  ]
};
