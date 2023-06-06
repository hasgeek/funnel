process.traceDeprecation = true;

const webpack = require('webpack');
const ESLintPlugin = require('eslint-webpack-plugin');
const path = require('path');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const { InjectManifest } = require('workbox-webpack-plugin');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

const nodeEnv = process.env.NODE_ENV || 'production';

module.exports = {
  resolve: {
    fallback: {
      fs: false,
      path: require.resolve('path-browserify'),
    },
  },
  cache: {
    type: 'filesystem',
    cacheDirectory: path.resolve(__dirname, '.webpack_cache'),
  },
  devtool: 'source-map',
  externals: {
    jquery: 'jQuery',
  },
  entry: {
    app: path.resolve(__dirname, 'funnel/assets/js/app.js'),
    index: path.resolve(__dirname, 'funnel/assets/js/index.js'),
    project_header: path.resolve(__dirname, 'funnel/assets/js/project_header.js'),
    project: path.resolve(__dirname, 'funnel/assets/js/project.js'),
    submissions: path.resolve(__dirname, 'funnel/assets/js/submissions.js'),
    submission: path.resolve(__dirname, 'funnel/assets/js/submission.js'),
    labels: path.resolve(__dirname, 'funnel/assets/js/labels.js'),
    schedule_view: path.resolve(__dirname, 'funnel/assets/js/schedule_view.js'),
    event: path.resolve(__dirname, 'funnel/assets/js/event.js'),
    scan_badge: path.resolve(__dirname, 'funnel/assets/js/scan_badge.js'),
    scan_contact: path.resolve(__dirname, 'funnel/assets/js/scan_contact.js'),
    contact: path.resolve(__dirname, 'funnel/assets/js/contact.js'),
    search: path.resolve(__dirname, 'funnel/assets/js/search.js'),
    membership: path.resolve(__dirname, 'funnel/assets/js/membership.js'),
    comments: path.resolve(__dirname, 'funnel/assets/js/comments.js'),
    update: path.resolve(__dirname, 'funnel/assets/js/update.js'),
    rsvp_list: path.resolve(__dirname, 'funnel/assets/js/rsvp_list.js'),
    notification_list: path.resolve(__dirname, 'funnel/assets/js/notification_list.js'),
    notification_settings: path.resolve(
      __dirname,
      'funnel/assets/js/notification_settings.js'
    ),
    account_saved: path.resolve(__dirname, 'funnel/assets/js/account_saved.js'),
    autosave_form: path.resolve(__dirname, 'funnel/assets/js/autosave_form.js'),
    form: path.resolve(__dirname, 'funnel/assets/js/form.js'),
    account_form: path.resolve(__dirname, 'funnel/assets/js/account_form.js'),
    submission_form: path.resolve(__dirname, 'funnel/assets/js/submission_form.js'),
    labels_form: path.resolve(__dirname, 'funnel/assets/js/labels_form.js'),
    cfp_form: path.resolve(__dirname, 'funnel/assets/js/cfp_form.js'),
    rsvp_form_modal: path.resolve(__dirname, 'funnel/assets/js/rsvp_form_modal.js'),
    app_css: path.resolve(__dirname, 'funnel/assets/sass/app.scss'),
    form_css: path.resolve(__dirname, 'funnel/assets/sass/form.scss'),
    index_css: path.resolve(__dirname, 'funnel/assets/sass/pages/index.scss'),
    profile_css: path.resolve(__dirname, 'funnel/assets/sass/pages/profile.scss'),
    project_css: path.resolve(__dirname, 'funnel/assets/sass/pages/project.scss'),
    submission_css: path.resolve(__dirname, 'funnel/assets/sass/pages/submission.scss'),
    labels_css: path.resolve(__dirname, 'funnel/assets/sass/pages/labels.scss'),
    schedule_css: path.resolve(__dirname, 'funnel/assets/sass/pages/schedule.scss'),
    about_css: path.resolve(__dirname, 'funnel/assets/sass/pages/about.scss'),
    login_form_css: path.resolve(__dirname, 'funnel/assets/sass/pages/login_form.scss'),
    comments_css: path.resolve(__dirname, 'funnel/assets/sass/pages/comments.scss'),
    scan_badge_css: path.resolve(__dirname, 'funnel/assets/sass/pages/scan_badge.scss'),
    contacts_css: path.resolve(__dirname, 'funnel/assets/sass/pages/contacts.scss'),
    submissions_css: path.resolve(
      __dirname,
      'funnel/assets/sass/pages/submissions.scss'
    ),
    membership_css: path.resolve(__dirname, 'funnel/assets/sass/pages/membership.scss'),
    account_css: path.resolve(__dirname, 'funnel/assets/sass/pages/account.scss'),
    update_css: path.resolve(__dirname, 'funnel/assets/sass/pages/update.scss'),
    imgee_modal_css: path.resolve(
      __dirname,
      'funnel/assets/sass/pages/imgee_modal.scss'
    ),
    label_form_css: path.resolve(__dirname, 'funnel/assets/sass/pages/label_form.scss'),
    submission_form_css: path.resolve(
      __dirname,
      'funnel/assets/sass/pages/submission_form.scss'
    ),
    screens_css: path.resolve(__dirname, 'funnel/assets/sass/pages/screens.scss'),
    event_css: path.resolve(__dirname, 'funnel/assets/sass/pages/event.scss'),
  },
  output: {
    path: path.resolve(__dirname, 'funnel/static/build'),
    publicPath: '/static/build/',
    filename: 'js/[name].[chunkhash].js',
  },
  module: {
    rules: [
      {
        enforce: 'pre',
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        options: {
          plugins: ['@babel/plugin-syntax-dynamic-import'],
          cacheCompression: false,
          cacheDirectory: true,
        },
      },
      {
        test: /\.scss$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'file-loader',
            options: { outputPath: 'css/', name: '[name].[hash].css' },
          },
          'sass-loader',
        ],
      },
    ],
  },
  plugins: [
    new ESLintPlugin({
      fix: true,
      cache: true,
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: 'node_modules/footable/css/fonts',
          to: 'css/fonts',
        },
        {
          from: 'node_modules/leaflet/dist/images',
          to: 'css/images',
        },
        {
          from: 'node_modules/prismjs/components/*.min.js',
          to: 'js/prismjs/components/[name].js',
        },
      ],
    }),
    new webpack.DefinePlugin({
      'process.env': { NODE_ENV: JSON.stringify(nodeEnv) },
    }),
    new CleanWebpackPlugin({
      root: path.join(__dirname, 'funnel/static'),
    }),
    new WebpackManifestPlugin({
      fileName: path.join(__dirname, 'funnel/static/build/manifest.json'),
    }),
    new InjectManifest({
      swSrc: path.resolve(__dirname, 'funnel/assets/service-worker-template.js'),
      swDest: path.resolve(__dirname, 'funnel/static/build/js/service-worker.js'),
    }),
  ],
};
