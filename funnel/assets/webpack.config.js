process.traceDeprecation = true;

const webpack = require('webpack');
const ESLintPlugin = require('eslint-webpack-plugin');
const path = require('path');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const { InjectManifest } = require('workbox-webpack-plugin');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');

const nodeEnv = process.env.NODE_ENV || 'production';

module.exports = {
  resolve: {
    fallback: {
      fs: false,
      path: require.resolve('path-browserify'),
    },
  },
  devtool: 'source-map',
  entry: {
    app: path.resolve(__dirname, 'js/app.js'),
    index: path.resolve(__dirname, 'js/index.js'),
    project_header: path.resolve(__dirname, 'js/project_header.js'),
    project: path.resolve(__dirname, 'js/project.js'),
    submissions: path.resolve(__dirname, 'js/submissions.js'),
    submission: path.resolve(__dirname, 'js/submission.js'),
    labels: path.resolve(__dirname, 'js/labels.js'),
    schedule_view: path.resolve(__dirname, 'js/schedule_view.js'),
    event: path.resolve(__dirname, 'js/event.js'),
    scan_badge: path.resolve(__dirname, 'js/scan_badge.js'),
    scan_contact: path.resolve(__dirname, 'js/scan_contact.js'),
    contact: path.resolve(__dirname, 'js/contact.js'),
    search: path.resolve(__dirname, 'js/search.js'),
    membership: path.resolve(__dirname, 'js/membership.js'),
    comments: path.resolve(__dirname, 'js/comments.js'),
    update: path.resolve(__dirname, 'js/update.js'),
    rsvp_list: path.resolve(__dirname, 'js/rsvp_list.js'),
    notification_list: path.resolve(__dirname, 'js/notification_list.js'),
    notification_settings: path.resolve(
      __dirname,
      'js/notification_settings.js'
    ),
    account_saved: path.resolve(__dirname, 'js/account_saved.js'),
    form: path.resolve(__dirname, 'js/form.js'),
    submission_form: path.resolve(__dirname, 'js/submission_form.js'),
    labels_form: path.resolve(__dirname, 'js/labels_form.js'),
    cfp_form: path.resolve(__dirname, 'js/cfp_form.js'),
    app_css: path.resolve(__dirname, 'sass/app.scss'),
    index_css: path.resolve(__dirname, 'sass/index.scss'),
    profile_css: path.resolve(__dirname, 'sass/profile.scss'),
    project_css: path.resolve(__dirname, 'sass/project.scss'),
    submission_css: path.resolve(__dirname, 'sass/submission.scss'),
    labels_css: path.resolve(__dirname, 'sass/labels.scss'),
    schedule_css: path.resolve(__dirname, 'sass/schedule.scss'),
    about_css: path.resolve(__dirname, 'sass/about.scss'),
    form_css: path.resolve(__dirname, 'sass/form.scss'),
    loginform_css: path.resolve(__dirname, 'sass/loginform.scss'),
    comments_css: path.resolve(__dirname, 'sass/comments.scss'),
    scanbadge_css: path.resolve(__dirname, 'sass/scanbadge.scss'),
    contacts_css: path.resolve(__dirname, 'sass/contacts.scss'),
    submissions_css: path.resolve(__dirname, 'sass/submissions.scss'),
    membership_css: path.resolve(__dirname, 'sass/membership.scss'),
    account_css: path.resolve(__dirname, 'sass/account.scss'),
    update_css: path.resolve(__dirname, 'sass/update.scss'),
    imgeemodal_css: path.resolve(__dirname, 'sass/imgee-modal.scss'),
  },
  output: {
    path: path.resolve(__dirname, '../static/build'),
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
    }),
    new webpack.DefinePlugin({
      'process.env': { NODE_ENV: JSON.stringify(nodeEnv) },
    }),
    new CleanWebpackPlugin({
      root: path.join(__dirname, '../static'),
    }),
    new WebpackManifestPlugin({
      fileName: path.join(__dirname, '../static/build/manifest.json'),
    }),
    new InjectManifest({
      swSrc: path.resolve(__dirname, 'service-worker-template.js'),
      swDest: path.resolve(__dirname, '../static/build/js/service-worker.js'),
    }),
  ],
};
