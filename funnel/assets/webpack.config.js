process.traceDeprecation = true;

const webpack = require('webpack');
const nodeEnv = process.env.NODE_ENV || 'production';
const path = require('path');
const cleanWebpackPlugin = require('clean-webpack-plugin');
const { InjectManifest } = require('workbox-webpack-plugin');

function ManifestPlugin(options) {
  this.manifestPath = options.manifestPath
    ? options.manifestPath
    : 'build/manifest.json';
}

ManifestPlugin.prototype.apply = function(compiler) {
  compiler.plugin('done', stats => {
    var stats_json = stats.toJson();
    var parsed_stats = {
      assets: stats_json.assetsByChunkName,
    };
    if (stats && stats.hasErrors()) {
      stats_json.errors.forEach(err => {
        console.error(err);
      });
    }
    Object.keys(parsed_stats.assets).forEach(function(key) {
      if (typeof parsed_stats.assets[key] == 'object') {
        for (var index in parsed_stats.assets[key]) {
          if (
            parsed_stats.assets[key][index].indexOf('.js') !== -1 &&
            parsed_stats.assets[key][index].indexOf('.map') == -1
          ) {
            parsed_stats.assets[key] = parsed_stats.assets[key][index];
          }
        }
      }
    });
    require('fs').writeFileSync(
      path.join(__dirname, this.manifestPath),
      JSON.stringify(parsed_stats)
    );
  });
};

module.exports = {
  node: {
    fs: 'empty',
  },
  devtool: 'source-map',
  entry: {
    app: path.resolve(__dirname, 'js/app.js'),
    index: path.resolve(__dirname, 'js/index.js'),
    project: path.resolve(__dirname, 'js/project.js'),
    proposals: path.resolve(__dirname, 'js/proposals.js'),
    proposal: path.resolve(__dirname, 'js/proposal.js'),
    schedule_view: path.resolve(__dirname, 'js/schedule_view.js'),
    event: path.resolve(__dirname, 'js/event.js'),
    scan_badge: path.resolve(__dirname, 'js/scan_badge.js'),
    scan_contact: path.resolve(__dirname, 'js/scan_contact.js'),
    contact: path.resolve(__dirname, 'js/contact.js'),
    search: path.resolve(__dirname, 'js/search.js'),
  },
  output: {
    path: path.resolve(__dirname, '../static/build'),
    publicPath: '/static/build/',
    filename: 'js/[name].[hash].js',
  },
  module: {
    rules: [
      {
        enforce: 'pre',
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        query: {
          plugins: ['@babel/plugin-syntax-dynamic-import'],
        },
      },
      {
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'eslint-loader',
        options: {
          fix: true,
          formatter: require('eslint/lib/cli-engine/formatters/stylish'),
        },
      },
    ],
  },
  plugins: [
    new webpack.DefinePlugin({
      'process.env': { NODE_ENV: JSON.stringify(nodeEnv) },
    }),
    new cleanWebpackPlugin(['build'], {
      root: path.join(__dirname, '../static'),
    }),
    new ManifestPlugin({ manifestPath: '../static/build/manifest.json' }),
    new InjectManifest({
      importWorkboxFrom: 'cdn',
      swSrc: path.resolve(__dirname, 'service-worker-template.js'),
      swDest: path.resolve(__dirname, '../static/service-worker.js'),
    }),
  ],
};
