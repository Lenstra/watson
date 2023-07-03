// Copyright (c) HashiCorp, Inc.
// SPDX-License-Identifier: MPL-2.0

package provider

import (
	"context"
	"fmt"

	"github.com/Lenstra/watson/internal/client"
	"github.com/hashicorp/terraform-plugin-framework/attr"
	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// Ensure provider defined types fully satisfy framework interfaces.
var (
	_ datasource.DataSource              = &OutputsDataSource{}
	_ datasource.DataSourceWithConfigure = &OutputsDataSource{}
)

func NewOutputsDataSource() datasource.DataSource {
	return &OutputsDataSource{}
}

// OutputsDataSource defines the data source implementation.
type OutputsDataSource struct {
	client *client.Client
}

// OutputsDataSourceModel describes the data source data model.
type OutputsDataSourceModel struct {
	Id      types.String `tfsdk:"id"`
	Stack   types.String `tfsdk:"stack"`
	Outputs types.Map    `tfsdk:"outputs"`
}

func (d *OutputsDataSource) Metadata(ctx context.Context, req datasource.MetadataRequest, resp *datasource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_outputs"
}

func (d *OutputsDataSource) Schema(ctx context.Context, req datasource.SchemaRequest, resp *datasource.SchemaResponse) {
	resp.Schema = schema.Schema{
		// This description is used by the documentation generator and the language server.
		MarkdownDescription: "Example data source",

		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				MarkdownDescription: "Example identifier",
				Computed:            true,
			},
			"stack": schema.StringAttribute{
				MarkdownDescription: "The stack to get the outputs of.",
				Required:            true,
			},
			"outputs": schema.MapAttribute{
				MarkdownDescription: "Example configurable attribute.",
				Computed:            true,
				ElementType: types.ObjectType{
					AttrTypes: map[string]attr.Type{
						"value":      types.StringType,
						"sensitive":  types.BoolType,
						"deprecated": types.StringType,
						"warning":    types.StringType,
					},
				},
			},
		},
	}
}

func (d *OutputsDataSource) Configure(ctx context.Context, req datasource.ConfigureRequest, resp *datasource.ConfigureResponse) {
	// Prevent panic if the provider has not been configured.
	if req.ProviderData == nil {
		return
	}

	client, ok := req.ProviderData.(*client.Client)

	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Data Source Configure Type",
			fmt.Sprintf("Expected *http.Client, got: %T. Please report this issue to the provider developers.", req.ProviderData),
		)

		return
	}

	d.client = client
}

func (d *OutputsDataSource) Read(ctx context.Context, req datasource.ReadRequest, resp *datasource.ReadResponse) {
	var data OutputsDataSourceModel

	// Read Terraform configuration data into the model
	resp.Diagnostics.Append(req.Config.Get(ctx, &data)...)

	if resp.Diagnostics.HasError() {
		return
	}

	stack := data.Stack.ValueString()
	data.Id = types.StringValue(stack)

	outputs, err := d.client.GetOutputs(stack)
	if err != nil {
		resp.Diagnostics.AddError(fmt.Sprintf("Failed to read outputs of %q", "stack"), err.Error())
		return
	}

	if outputs == nil {
		resp.Diagnostics.AddError("Unknown stack", fmt.Sprintf("No stack named %q could be found", stack))
		return
	}

	result := map[string]attr.Value{}
	for k, v := range *outputs {
		switch value := v.Value.(type) {
		case string:
			result[k] = types.ObjectValueMust(
				map[string]attr.Type{
					"value":      types.StringType,
					"sensitive":  types.BoolType,
					"deprecated": types.StringType,
					"warning":    types.StringType,
				},
				map[string]attr.Value{
					"value":      types.StringValue(value),
					"deprecated": types.StringValue(v.Deprecated),
					"warning":    types.StringValue(v.Warning),
					"sensitive":  types.BoolValue(v.Sensitive),
				},
			)

		default:
			resp.Diagnostics.AddWarning("ignored output", fmt.Sprintf("output %q has type %T and is ignored for now", k, value))
		}

		if v.Deprecated != "" {
			resp.Diagnostics.AddWarning(fmt.Sprintf("Output %s is deprecated", k), v.Deprecated)
		}

		if v.Deprecated != "" {
			resp.Diagnostics.AddWarning(fmt.Sprintf("The output %s has a warning", k), v.Warning)
		}
	}

	data.Outputs = types.MapValueMust(
		types.ObjectType{
			AttrTypes: map[string]attr.Type{
				"value":      types.StringType,
				"sensitive":  types.BoolType,
				"deprecated": types.StringType,
				"warning":    types.StringType,
			},
		},
		result,
	)

	// Save data into Terraform state
	resp.Diagnostics.Append(resp.State.Set(ctx, &data)...)
}
