process.traceDeprecation = true;

const webpack = require('webpack');
const nodeEnv = process.env.NODE_ENV || "production";
const path = require('path');
const cleanWebpackPlugin = require('clean-webpack-plugin');

function ManifestPlugin(options){
  this.manifestPath = options.manifestPath ? options.manifestPath : 'build/manifest.json';
}

ManifestPlugin.prototype.apply = function(compiler) {
  compiler.plugin('done', stats => {
    var stats_json = stats.toJson();
    var parsed_stats = {
      assets: stats_json.assetsByChunkName,
    }
    if (stats && stats.hasErrors()) {
      stats_json.errors.forEach((err) => {
          console.error(err);
      });
    }
    Object.keys(parsed_stats.assets).forEach(function(key) {
       console.log('parsed_stats.assets[key]', parsed_stats.assets[key]);
      if(typeof(parsed_stats.assets[key]) == "object") {
        for(var index in parsed_stats.assets[key]) {
          if(parsed_stats.assets[key][index].indexOf('.js') !== -1 && 
            parsed_stats.assets[key][index].indexOf('.map') == -1) {
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
}

module.exports = {
  devtool: 'source-map',
  entry: {
    "app": path.resolve(__dirname, "js/app.js"),
    "event": path.resolve(__dirname, "js/event.js"),
    "project": path.resolve(__dirname, "js/project.js"),
    "proposal": path.resolve(__dirname, "js/proposal.js"),
    "scan_badge": path.resolve(__dirname, "js/scan_badge.js"),
    "schedule_view": path.resolve(__dirname, "js/schedule_view.js"),
  },
  output: {
    path: path.resolve(__dirname,  "../static/build"),
    publicPath: path.resolve(__dirname, "../static/build"),
    filename:  "js/[name].[hash].js"
  },
  module: {
    rules: [
      {
        enforce: "pre",
        test: /\.js$/,
        exclude: /node_modules/,
        loader: "babel-loader",
      },
      {
        test: /\.js$/,
        exclude: /node_modules/,
        loader: "eslint-loader",
        options: {
          fix: true,
        },
      },
    ]
  },
  plugins: [
    new webpack.DefinePlugin({
      'process.env': { NODE_ENV: JSON.stringify(nodeEnv) }
    }),
    new cleanWebpackPlugin(['build'], {root: path.join(__dirname, '../static')}),
    new ManifestPlugin({manifestPath: '../static/build/manifest.json'})
  ]
};