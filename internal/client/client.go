package client

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/hashicorp/go-cleanhttp"
)

type Config struct {
	Address    string
	Scheme     string
	Stack      string
	HttpClient *http.Client
}

func DefaultConfig() *Config {
	config := &Config{
		Scheme:     "https",
		HttpClient: cleanhttp.DefaultPooledClient(),
	}

	if addr := os.Getenv("watson_ADDRESS"); addr != "" {
		config.Address = addr
	}
	if scheme := os.Getenv("watson_SCHEME"); scheme != "" {
		config.Scheme = scheme
	}
	if stack := os.Getenv("watson_STACK"); stack != "" {
		config.Stack = stack
	}

	return config
}

type Client struct {
	config  Config
	headers http.Header
}

func NewClient(config *Config) (*Client, error) {
	defConfig := DefaultConfig()
	if config.Address == "" {
		config.Address = defConfig.Address
	}
	if config.Scheme == "" {
		config.Scheme = defConfig.Scheme
	}
	if config.Stack == "" {
		config.Stack = defConfig.Stack
	}
	if config.HttpClient == nil {
		config.HttpClient = defConfig.HttpClient
	}

	parts := strings.SplitN(config.Address, "://", 2)
	if len(parts) == 2 {
		switch parts[0] {
		case "http":
			config.Scheme = "http"
		case "https":
			config.Scheme = "https"
		default:
			return nil, fmt.Errorf("unknown protocol scheme: %s", parts[0])
		}
		config.Address = parts[1]
	}

	headers := make(http.Header)
	if config.Stack != "" {
		headers.Set("x-watson-stack", config.Stack)
	}

	return &Client{config: *config, headers: headers}, nil
}

// doRequest runs a request with our client
func (c *Client) doRequest(path string) (*http.Response, error) {
	req, err := http.NewRequest("GET", path, nil)
	if err != nil {
		return nil, err
	}
	req.URL.Scheme = c.config.Scheme
	req.URL.Host = c.config.Address
	req.Header = c.headers
	return c.config.HttpClient.Do(req)
}

type Output struct {
	Value      interface{}
	Deprecated string
	Warning    string
}

type Outputs map[string]Output

func validateStackName(stack string) error {
	if strings.Count(stack, "/") != 1 {
		return fmt.Errorf("%q is not a valid stack name", stack)
	}

	return nil
}

func (c *Client) GetOutputs(stack string) (*Outputs, error) {
	if err := validateStackName(stack); err != nil {
		return nil, err
	}
	resp, err := c.doRequest(fmt.Sprintf("/v1/projects/%s/outputs/", stack))
	if err != nil {
		return nil, err
	}
	defer closeResponseBody(resp)
	switch code := resp.StatusCode; code {
	case 200:
		break
	case 404:
		return nil, nil
	default:
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var outputs Outputs
	dec := json.NewDecoder(resp.Body)
	if err := dec.Decode(&outputs); err != nil {
		return nil, err
	}

	return &outputs, nil
}

type Stack struct {
	Id     string `json:"id"`
	Name   string `json:"name"`
	URL    string `json:"url"`
	UsedBy []struct {
		Id         string    `json:"id"`
		URL        string    `json:"url"`
		LastUsedAt time.Time `json:"last_used_at"`
	} `json:"used_by"`
}

func (c *Client) GetStack(stack string) (*Stack, error) {
	if err := validateStackName(stack); err != nil {
		return nil, err
	}
	resp, err := c.doRequest(fmt.Sprintf("/v1/projects/%s/", stack))
	if err != nil {
		return nil, err
	}
	defer closeResponseBody(resp)
	switch code := resp.StatusCode; code {
	case 200:
		break
	case 404:
		return nil, nil
	default:
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var s Stack
	dec := json.NewDecoder(resp.Body)
	if err := dec.Decode(&s); err != nil {
		return nil, err
	}

	return &s, nil
}

func closeResponseBody(resp *http.Response) error {
	_, _ = io.Copy(io.Discard, resp.Body)
	return resp.Body.Close()
}
