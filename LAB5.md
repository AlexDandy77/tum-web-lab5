## Lab 5 - HTTP over TCP Sockets

1. You have to write a command line program:
2. The program should implement at least the following CLI:
  ```
  go2web -u <URL>         # make an HTTP request to the specified URL and print the response
  go2web -s <search-term> # make an HTTP request to search the term using your favorite search engine and print top 10 results
  go2web -h               # show this help
  ```
3. The responses from request should be human-readable (e.g. no HTML tags in the output)

## Special conditions

Any programming language can be used, but not the built-in/third-party libraries for making HTTP/HTTPS requests. GUI applications aren't allowed. The app has to be launched with `go2web` executable.

## Grading

Submission: 
- WIP PRs/commits done in class/same day of lab;
- Other PRs/commits for each tasks/extra points;
- In repo README include a gif with working example.

After submission you need to present the program in class to be graded.

Points:

- executable with `-h`, (`-u` or `-s`) options - `+5` points
- executable with `-h`, (`-u` and `-s`) options - `+6` points

You can get `+1` extra point:
- if results/links from search engine can be accessed (using your CLI);
- for implementing HTTP request redirects.

You can get `+2` extra points:
- for implementing an HTTP cache mechanism;
- for implementing content negotiation e.g. by accepting and handling both JSON and HTML content types.

You can get `-1` point for each unanswered question.  
You can get `-3` points for poor git history (ex: 1-2 commits).

## Hints

- Before opting for some language, make sure you have the right tools: CLI parser, HTML/JSON parser, support for TCP sockets;
- For CLI you can use built-in libraries or even Bash built-in [getopts](https://wiki.bash-hackers.org/howto/getopts_tutorial);
- Use third-party libraries for parsing HTML and presenting it;
- For HTTP cache you'll need either an in-memory store or file access;
- `<search-term>` can either be a single word or all words following `-s` argument.