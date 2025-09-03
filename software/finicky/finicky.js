// @ts-check

/**
 * @typedef {import('/Applications/Finicky.app/Contents/Resources/finicky.d.ts').FinickyConfig} FinickyConfig
 */

/**
 * @type {FinickyConfig}
 */
export default {
  defaultBrowser: 'Safari',
  rewrite: [
    // Redirect all urls to use https
    {
      match: (url) => (
        url.protocol === 'http' &&
        url.host !== 'localhost' &&
        url.host !== '127.0.0.1'
      ),
      url: (url) => ({ ...url, protocol: 'https' }),
    },
  ],
  handlers: [
    {
      match: finicky.matchHostnames(['localhost', '127.0.0.1', /\.local$/]),
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
  ],
};
