module.exports = {
  apps : [{
    name: 'beps_cdn_test',
    script: 'server.js',
    max_memory_restart: '120M',
    node_args: '--max-old-space-size=512',
    instances: 2,
    exec_mode: 'cluster',    
    out_file: "./logs/beps_cdn_test_out.log",
    error_file: "./logs/beps_cdn_test_error.log",
    log_date_format: "YYYY-MM-DD HH:mm:ss",
    max_restarts: 5,
    autorestart: true,
    watch: false
  }],
};

