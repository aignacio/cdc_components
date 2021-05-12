/**
 * File: cdc_2ff_w_ack.sv
 * Description: 2x Flip-Flop synchonizer with acknowledge
 * Author: Anderson Ignacio da Silva <aignacio@aignacio.com>
 *
 * MIT License
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
module cdc_2ff_w_ack # (
  parameter int DATA_WIDTH = 1 // Data width in bits
)(
  input                     arst_a,
  input                     arst_b,
  input                     clk_a_in,
  input                     clk_b_in,
  input   [DATA_WIDTH-1:0]  data_a_i,
  output                    ack_a_o,
  output  [DATA_WIDTH-1:0]  data_b_o
);
  logic [DATA_WIDTH-1:0]  data_a_ffs;

  always_ff @ (posedge clk_a_in or posedge arst_a) begin
    if (arst_a) begin
      data_a_ffs <= '0;
    end
    else begin
      data_a_ffs <= data_a_i;
    end
  end

  cdc_2ff_sync# (
    .DATA_WIDTH(1)
  ) u_ack_from_b (
    .arst_master(arst_a),
    .clk_sync   (clk_a_in),
    .async_i    (|data_b_o),
    .sync_o     (ack_a_o)
  );

  cdc_2ff_sync# (
    .DATA_WIDTH(DATA_WIDTH)
  ) u_sync_from_a (
    .arst_master(arst_b),
    .clk_sync   (clk_b_in),
    .async_i    (data_a_ffs),
    .sync_o     (data_b_o)
  );
endmodule
