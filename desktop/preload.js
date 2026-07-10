// Director-bot preload: minimal bridge for the dashboard renderer.
'use strict';

const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('directorBotNative', {
  platform: process.platform,
  isDesktop: true,
});
